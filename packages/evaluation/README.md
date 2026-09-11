# Evaluation package

`agas_evaluation` turns planning artifacts into identity-free behavioral signatures and compares
paired counterfactuals against explicit expectations. It reports per-dimension similarity and
raises a generic-program alert when a declared meaningful response does not occur. It also catches
changes to dimensions the counterfactual says must remain stable.

The analyzer does not declare every highly similar plan generic. A focused one-variable change
should normally preserve most of a plan, so every evaluation must state which dimensions must
change and which must remain stable. Synthetic fixtures remain non-operational and do not establish
training policy or scientific thresholds.
