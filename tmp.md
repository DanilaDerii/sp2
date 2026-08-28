set up test kit to test difrent llms agaisnt certain pack by quering lms server (send quires to lm studio language models and check response geenration time)


make install script start back end seerver automatically , but list comand to start server nonethe less for future starts



add loading installed llm to server in install script same as embeder model


We should improve retrieval so repeated cover pages cannot consume all results. The safest approach is to retrieve more candidates, remove repetitive/title-only results, and then return the best five useful chunks. We should not simply remove every short chunk because some short pages, such as “Objectives of Testing,” are valuable.
