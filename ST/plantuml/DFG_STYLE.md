# Lecturer DFG style

For this coursework, match the style accepted in the photographed `CALCULATE_GRADE` examination answer. The lecturer calls this a **data flow graph (DFG)** even though its structure is similar to a program control-flow graph.

## Required notation

- Begin with a numbered entry node containing the function parameters and relevant global values.
- Put a bold `N#` heading inside every rendered node, matching the current PlantUML DFG style.
- Use numbered rectangles for actual assignments, calculations, calls, and returns.
- Combine consecutive variable bindings, assignments, and initialization statements into one node when no decision, loop, or exception boundary separates them.
- Copy conditional expressions from the code into decision diamonds. Do not paraphrase or invert them.
- Label predicate edges `T` and `F`.
- Use a `Null` node when control paths merge without executing a statement, but do not add one after PlantUML has already generated a visible merge point.
- Show loop-back edges explicitly.
- Put the actual returned expression or values in the final return node.

## Data-flow analysis

After numbering the graph, identify data usage from those nodes:

- `def(x)`: the node assigns or initializes `x`.
- `c-use(x)`: the node uses `x` in a calculation, assignment, call, or return.
- `p-use(x)`: a decision edge uses `x` in a predicate.
- A DU path connects a `def(x)` to a reachable use of `x` without another definition of `x` on the path.
- Function parameters count as entry definitions.
- Record exit undefinitions if required by the marking scheme.
- Def/use sets and DU-path notes may remain as non-rendered PlantUML comments so the visible graph stays close to the lecturer's example.

## Avoid

- System-level data-flow diagrams with services, databases, or external actors.
- A dependency-only graph that removes the function's decisions and loops.
- Verbal nodes such as "process the input" when an exact code statement is available.
- Invented conditions, assignments, or helper operations that do not occur in the code.
- Unnumbered merge points or unexplained routing nodes.

The result should preserve the function's executable structure while making definitions, computational uses, predicate uses, and DU paths traceable.
