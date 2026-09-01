"""Isolated unit tests for the two standalone SP2 mini pipelines."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from ST.mini import mini_ingestion as ingestion
from ST.mini import mini_retrieval as retrieval


class FakePdfPage:
    def __init__(self, text: str) -> None:
        self.text = text

    def get_text(self, mode: str, *, sort: bool) -> str:
        return self.text


class FakePdf:
    def __init__(self, page_texts: list[str]) -> None:
        self.pages = [FakePdfPage(text) for text in page_texts]

    def __enter__(self):
        return iter(self.pages)

    def __exit__(self, exception_type, exception, traceback) -> None:
        return None


class MiniIngestionTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(temporary_directory.cleanup)
        self.pdf_path = Path(temporary_directory.name) / "course.pdf"
        self.pdf_path.write_bytes(b"unit-test placeholder")

    def test_success_preserves_overlap_metadata_and_storage_flow(self) -> None:
        embedder_calls: list[tuple[list[str], str]] = []

        def fake_embedder(texts: list[str], *, model: str) -> list[list[float]]:
            embedder_calls.append((texts, model))
            return [[0.25] * ingestion.EMBEDDING_DIMENSION for _ in texts]

        export_pack = Mock()
        install_pack = Mock()
        insert_sqlite = Mock(return_value=17)
        insert_lance = Mock(return_value=2)

        with (
            patch.object(ingestion, "_open_pdf", return_value=FakePdf(["abcdefgh"])),
            patch.object(ingestion, "_pack_is_installed", return_value=False),
            patch.object(ingestion, "_export_pack_zip", export_pack),
            patch.object(ingestion, "_install_pack_files", install_pack),
            patch.object(ingestion, "_insert_sqlite_metadata", insert_sqlite),
            patch.object(ingestion, "_insert_lancedb_chunks", insert_lance),
        ):
            result = ingestion.mini_ingest_pdf(
                self.pdf_path,
                pack_id="course",
                title="Course",
                embedder=fake_embedder,
                chunk_size=5,
                overlap=2,
            )

        self.assertEqual(
            embedder_calls[0][0],
            ["search_document: abcde", "search_document: defgh"],
        )
        self.assertEqual(embedder_calls[0][1], ingestion.EMBEDDING_MODEL)

        metadata, chunk_records, vector_rows, zip_path = export_pack.call_args.args
        self.assertEqual(metadata["embedding_dim"], ingestion.EMBEDDING_DIMENSION)
        self.assertEqual([record["page"] for record in chunk_records], [1, 1])
        self.assertEqual([record["chunk_index"] for record in chunk_records], [0, 1])
        self.assertEqual(len(vector_rows), 2)
        self.assertEqual([len(vector) for vector in vector_rows], [768, 768])
        install_pack.assert_called_once_with(zip_path, ingestion.INSTALLED_PACKS_DIR / "course-v1")

        embedded_chunks = insert_lance.call_args.args[0]
        self.assertEqual([item.chunk.text for item in embedded_chunks], ["abcde", "defgh"])
        self.assertEqual(result.installed_pack_id, 17)
        self.assertEqual(result.chunk_count, 2)

    def test_invalid_chunk_domains_are_rejected_before_storage(self) -> None:
        invalid_domains = (
            {"chunk_size": 0, "overlap": 0},
            {"chunk_size": 5, "overlap": -1},
            {"chunk_size": 5, "overlap": 5},
        )

        for domain in invalid_domains:
            with self.subTest(domain=domain):
                with self.assertRaises(ValueError):
                    ingestion.mini_ingest_pdf(
                        self.pdf_path,
                        pack_id="course",
                        title="Course",
                        embedder=Mock(),
                        **domain,
                    )

    def test_duplicate_is_rejected_before_pdf_or_embedding_calls(self) -> None:
        pdf_open = Mock()
        embedder = Mock()
        with (
            patch.object(ingestion, "_pack_is_installed", return_value=True),
            patch.object(ingestion, "_open_pdf", pdf_open),
        ):
            with self.assertRaises(FileExistsError):
                ingestion.mini_ingest_pdf(
                    self.pdf_path,
                    pack_id="course",
                    title="Course",
                    embedder=embedder,
                )

        pdf_open.assert_not_called()
        embedder.assert_not_called()

    def test_blank_pdf_produces_no_chunks(self) -> None:
        with (
            patch.object(ingestion, "_pack_is_installed", return_value=False),
            patch.object(ingestion, "_open_pdf", return_value=FakePdf([" \n "])),
        ):
            with self.assertRaisesRegex(ValueError, "no searchable chunks"):
                ingestion.mini_ingest_pdf(
                    self.pdf_path,
                    pack_id="course",
                    title="Course",
                    embedder=Mock(),
                )

    def test_embedding_count_must_equal_chunk_count(self) -> None:
        with (
            patch.object(ingestion, "_pack_is_installed", return_value=False),
            patch.object(ingestion, "_open_pdf", return_value=FakePdf(["content"])),
        ):
            with self.assertRaisesRegex(ValueError, "embedding count"):
                ingestion.mini_ingest_pdf(
                    self.pdf_path,
                    pack_id="course",
                    title="Course",
                    embedder=lambda texts, **kwargs: [],
                )

    def test_ingestion_embedding_dimension_must_be_768(self) -> None:
        with (
            patch.object(ingestion, "_pack_is_installed", return_value=False),
            patch.object(ingestion, "_open_pdf", return_value=FakePdf(["content"])),
        ):
            with self.assertRaisesRegex(ValueError, "dimension must be 768"):
                ingestion.mini_ingest_pdf(
                    self.pdf_path,
                    pack_id="course",
                    title="Course",
                    embedder=lambda texts, **kwargs: [[0.0, 1.0]],
                )


class MiniRetrievalTests(unittest.TestCase):
    def active_pack(self, **changes) -> retrieval.MiniInstalledPack:
        values = {
            "installed_pack_id": 9,
            "pack_id": "course",
            "embedding_model": retrieval.SUPPORTED_EMBEDDING_MODEL,
            "embedding_dimension": 768,
            "default_top_k": 4,
            "is_active": True,
        }
        values.update(changes)
        return retrieval.MiniInstalledPack(**values)

    def candidate(self, *, distance: float) -> dict:
        return {
            "chunk_id": f"chunk-{distance}",
            "installed_pack_id": 9,
            "pack_id": "course",
            "source_id": "course.pdf",
            "source_type": "pdf",
            "source_title": "course.pdf",
            "text": "retrieved text",
            "chunk_index": 3,
            "page": 2,
            "section": "Section",
            "_distance": distance,
        }

    def test_success_uses_pack_model_filter_limit_distance_and_score(self) -> None:
        embedder_calls: list[tuple[list[str], str]] = []

        def fake_embedder(texts: list[str], *, model: str) -> list[list[float]]:
            embedder_calls.append((texts, model))
            return [[0.0] * 768]

        search = Mock(
            return_value=[
                self.candidate(distance=0.25),
                self.candidate(distance=1.25),
            ]
        )
        with (
            patch.object(retrieval, "_find_installed_pack", return_value=self.active_pack()),
            patch.object(retrieval, "_search_candidate_rows", search),
        ):
            result = retrieval.mini_retrieve_course_context(
                installed_pack_id=9,
                question="  what   is testing? ",
                embedder=fake_embedder,
                max_distance=1.0,
            )

        self.assertEqual(embedder_calls[0][0], ["search_query: what is testing?"])
        self.assertEqual(embedder_calls[0][1], retrieval.SUPPORTED_EMBEDDING_MODEL)
        search.assert_called_once_with([0.0] * 768, 9, 4)
        self.assertEqual(result.mode, "course_context")
        self.assertEqual(len(result.chunks), 1)
        self.assertAlmostEqual(result.chunks[0].score, 0.8)
        self.assertEqual(result.chunks[0].page, 2)

    def test_above_distance_candidates_return_no_context(self) -> None:
        with (
            patch.object(retrieval, "_find_installed_pack", return_value=self.active_pack()),
            patch.object(
                retrieval,
                "_search_candidate_rows",
                return_value=[self.candidate(distance=0.6)],
            ),
        ):
            result = retrieval.mini_retrieve_course_context(
                installed_pack_id=9,
                question="question",
                embedder=lambda texts, **kwargs: [[0.0] * 768],
                max_distance=0.5,
            )

        self.assertEqual(result.mode, "no_course_context")
        self.assertEqual(result.chunks, [])

    def test_invalid_request_domains_are_rejected(self) -> None:
        for invalid_id in (True, 0, -1):
            with self.subTest(installed_pack_id=invalid_id):
                with self.assertRaises(ValueError):
                    retrieval.mini_retrieve_course_context(
                        installed_pack_id=invalid_id,
                        question="question",
                        embedder=Mock(),
                    )

        with self.assertRaisesRegex(ValueError, "question must not be empty"):
            retrieval.mini_retrieve_course_context(
                installed_pack_id=1,
                question=" \n ",
                embedder=Mock(),
            )

    def test_missing_inactive_and_wrong_model_packs_are_rejected(self) -> None:
        cases = (
            (None, LookupError),
            (self.active_pack(is_active=False), ValueError),
            (self.active_pack(embedding_model="wrong-model"), ValueError),
        )

        for installed_pack, expected_error in cases:
            with self.subTest(installed_pack=installed_pack):
                with patch.object(
                    retrieval,
                    "_find_installed_pack",
                    return_value=installed_pack,
                ):
                    with self.assertRaises(expected_error):
                        retrieval.mini_retrieve_course_context(
                            installed_pack_id=9,
                            question="question",
                            embedder=Mock(),
                        )

    def test_invalid_search_domains_are_rejected_before_embedding(self) -> None:
        embedder = Mock()
        cases = (
            {"top_k": True},
            {"top_k": 0},
            {"max_distance": True},
            {"max_distance": -0.1},
        )

        with patch.object(
            retrieval,
            "_find_installed_pack",
            return_value=self.active_pack(),
        ):
            for search_domain in cases:
                with self.subTest(search_domain=search_domain):
                    with self.assertRaises(ValueError):
                        retrieval.mini_retrieve_course_context(
                            installed_pack_id=9,
                            question="question",
                            embedder=embedder,
                            **search_domain,
                        )

        embedder.assert_not_called()

    def test_query_vector_contract_is_enforced(self) -> None:
        invalid_vectors = (
            [],
            [[0.0] * 768, [0.0] * 768],
            [[0.0, 1.0]],
            [["not-numeric"] * 768],
        )

        with patch.object(
            retrieval,
            "_find_installed_pack",
            return_value=self.active_pack(),
        ):
            for vectors in invalid_vectors:
                with self.subTest(vector_count=len(vectors)):
                    with self.assertRaises(ValueError):
                        retrieval.mini_retrieve_course_context(
                            installed_pack_id=9,
                            question="question",
                            embedder=lambda texts, **kwargs: vectors,
                        )


if __name__ == "__main__":
    unittest.main()
