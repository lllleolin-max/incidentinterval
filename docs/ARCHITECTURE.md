# Algorithm and trust boundary

`domain.py` checks the strict integer contract and resource cardinality. `temporal.py` implements a simple temporal network (STN). `engine.py` intersects observations with explicitly supplied max-plus structural hypotheses and their bounded interventions. `checker.py` independently checks equations against certificate times/delays without calling the solver. `cli.py` handles strict local JSON, duplicate keys, file byte limits and stable exit statuses. Core SDK functions do not write files, execute commands, access the network or change the incident input.

## Temporal network

Every event interval L ≤ t ≤ U is two inequalities relative to `@origin`; every measured difference L ≤ t[v]-t[u] ≤ U is two directed weighted edges. Bellman-Ford with all-zero initial potentials detects any negative cycle, including disconnected components. Following predecessor edges V times enters a cycle; its ordered edges are returned and checked. Otherwise normalized potentials give an integer feasible assignment with origin zero. Floyd-Warshall provides tight bounds on every pair: `[-d[v][u], d[u][v]]`. All arithmetic on reachable paths uses Python integers; no floating-point epsilon decides equality or infeasibility.

Bellman-Ford costs O(VE); closure costs O(V^3), memory O(V²+E). Canonical node and edge order makes equivalent input permutations stable. The certificate checker costs O(E). Source IDs are carried by each corresponding interval/difference inequality. The solver proves consistency of declared data, not source accuracy.

## Max-plus structural equations

A DAG root has a declared interval. Every nonroot satisfies

```text
t[v] = max(t[u] + delay[u,v] for all incoming links)
delay[u,v] ∈ [L[u,v], U[u,v]] independently
```

For fixed times, this is equivalent to (1) `t[v] >= t[u] + L` for every incoming edge, and (2) `t[v] <= t[u] + U` for at least one incoming edge. Choose that edge's delay `t[v]-t[u]`; choose minimum delays on every other edge. The lower inequalities ensure no other arrival exceeds `t[v]`. This constructive equivalence makes the max equation a finite union of STNs, one branch per critical-parent choice. We enumerate all choices within a cap; we never declare a model feasible merely because interval envelopes overlap. Envelopes derived recursively from roots/lag bounds provide sound finite support and cheap necessary constraints.

For indegrees d[v], B=∏d[v] branches, worst-case per model O(B(V³+VE)) time and O(BV²) retained feasible closure memory. An incident evaluates H models and up to 2HI historical/scenario solves; this multiplies the cost. In addition to the per-model branch cap, a shared analysis budget precharges every solve `V*E + V^3` (or `V*E` without closure), including extremum witnesses. This prevents many individually permitted models/actions from bypassing the workflow bound. A partially enumerated model becomes UNKNOWN, with no exact range/feasibility claim from sampled branches. Root mismatch/cycles are invalid structural models; excessive branch/work limits return UNKNOWN. Necessary temporal contradiction can refute a model even when B exceeds the branch cap if its solve fits the work budget. A contradiction of the exact max model with feasible necessary constraints includes a negative-cycle witness for **every** complete selector, not one failing branch presented as exhaustive proof.

Package 0.2.0 traverses selectors in the same canonical depth-first order. At a
multiple-choice node with more than one suffix assignment, it checks the base
constraints plus the selected upper edges using Bellman-Ford without closure.
A negative cycle has a strictly negative sum despite its telescoping time
differences summing to zero. Every extension only adds inequalities, so no
extension can restore feasibility. The engine skips suffix solves and emits the
full selector identities with that cycle. Single-choice prefixes and complete
leaves receive no extra prefix check; every feasible leaf still receives full
closure. Feasible selector sets, duration endpoints and conditional decisions
therefore retain their complete meaning.

Prefix checks are individually precharged to the same WorkBudget. In the
all-feasible case they add Bellman-Ford work without eliminating a single leaf;
this is a measured adverse case, not an unconditional speedup. The branching
prefix tree has fewer than 2B checked edges, so the asymptotic worst-case bound
remains exponential. Initial necessary-constraint closure still costs O(V²)
memory, and all feasible leaf closures remain retained. The complete failure
record list and serialized repeated cycles can also grow with B; this change
does not promise compact reports or constant memory.

`check_model_contradiction` implements its own DAG/envelope and inequality
reconstruction, checks the supplied base constraints, and checks every selector
identity for membership, uniqueness and complete coverage. Each cycle is checked
for exact edge membership, connected closure and a negative integer sum. It
calls neither the engine graph helpers nor the STN solver. New metadata is
type/accounting checked; absence supports the legacy v1 format. It verifies
logical contradiction, not source authenticity or actual execution counters.

Impact duration min/max is optimized separately in every feasible STN, then across the union. Each extremum is attained by adding a difference equality and solving again; the direct equation checker can verify the resulting witness, critical-parent ID, exact integer domain and claimed duration. The witness alone proves attainment, not global optimality: the exhaustive branch/closure algorithm establishes the global bounds, tested against independent small integer enumeration. The intervention checker separately rebuilds reachability, altered equations and observation relaxation, without using engine helpers. We report the min/max envelope and do not assert every interior value is feasible. Critical-parent alternatives come from all feasible branch selectors; a selected parent's zero/tied delay still permits a causal DAG but does not force strict chronological order. Invalid causal models include an independently checkable closed link-ID cycle, not a false negative temporal cycle.

## Interventions

Root windows or link delays can change; node removal cascades along necessary-prerequisite edges. Historical compatibility uses all observations and the changed model, reporting why it conflicts. Counterfactuals relax event bounds and time differences touching affected descendants; unaffected constraints remain. Source observations are not modified. Root activation/lag windows continue as model assumptions. All changes and conditions are reported.

The model assumes independent delay intervals and no omitted causal mechanisms. An exact range under these assumptions is not an identified real-world effect. Comparing baseline/scenario min/max yields a conservative unpaired improvement envelope; it can leave an action unidentified when a more detailed coupled model would resolve it. Alternative hypotheses are separate structural explanations, not weighted probabilities. Evidence presence allows a conditional recommendation but does not validate causality. An unknown hypothesis blocks a recommendation robust across the supplied set.

## Supported subset / failure boundaries

Useful scope: tens of significant incident events, finite integer clock intervals, difference observations, DAG AND-gated prerequisites, independent bounded link delays, uncertain root times, complete enumeration within limits, and explicit counterfactual modifications. Unsupported: OR triggers inside one graph, feedback/cyclic dynamics, stochastic/continuous probability models, partial correlations of delays, unobserved event discovery, natural-language extraction, clock offset estimation and authenticated source retrieval. Encode OR causes as separate hypotheses only when that is an honest model; changing the graph to avoid a contradiction does not count as causal proof.

Input cardinality/byte bounds and branch limits constrain work, but this library is not a sandbox or a service isolation layer. Reports can include incident labels, source references and constraints; sanitize data before persistence. Users control how outward-quantized integer windows approximate clock error. An interval crossing an endpoint is inclusive by design, with equal-time relations explicitly retained.
