# The ML implementation track

`reps` has two tracks. The **coding** track is Blind 75. The **ml** track is for practicing turning
math into NumPy/PyTorch code from a blank editor — softmax, attention, layernorm, a backward pass,
k-means — the "ML coding & debugging" interview stage. Both tracks share one SM-2 schedule; the deck
toggle in the UI is just a view. Use **What's next?** with the ML deck active to drill ML under spaced
repetition.

**Scope rule:** the ml track is only for drills that *execute and produce a checkable numeric answer*.
Conceptual questions ("why does BatchNorm help") have no executable output and do not belong here —
keep those on physical cards.

## The decks

| Source | What it is | Verified by |
|---|---|---|
| **TensorPuzzles** | 21 broadcasting puzzles ported from [Sasha Rush's Tensor-Puzzles](https://github.com/srush/Tensor-Puzzles). Implement `ones`, `cumsum`, `outer`, `bincount`, … in one line of broadcasting, no loops or shortcut ops. | The user's output vs a nested-loop reference; a `banned` list blocks the shortcut ops via an AST check. |
| **AutodiffPuzzles** | 10 backward-pass drills in the spirit of [Autodiff-Puzzles](https://github.com/srush/Autodiff-Puzzles). Given a forward `f`, implement its gradient. Highest-ROI for RS/RE interviews. | Your gradient vs `torch.autograd.grad` on random inputs. |
| **ClassicML** | 12 original from-scratch NumPy problems (linear/logistic regression, k-means, PCA, k-NN, metrics, naive Bayes, …), in the spirit of deep-ml.com's categories. | Your output vs a reference implementation on random inputs (`np.allclose`). |
| **ML-Impl** | ~10 interview-critical implementation drills: stable softmax, cross-entropy, layernorm, an MLP forward/backward, self- and causal attention, a k-means step. | Reference + random tests (`np.allclose`). |

**deep-ml.com stays an external companion.** It has its own online judge; we don't scrape it. This deck
is the offline, reps-scheduled subset you drill here — original problems, not copies of theirs.

## Schema — the ML fields

ML problems are the same `Problem` JSON as coding problems, with these optional fields (all default to a
coding-safe value, so the 76 coding problems are unaffected):

| Field | Meaning |
|---|---|
| `track` | `"coding"` (default) or `"ml"` — the deck. |
| `libraries` | e.g. `["numpy"]` or `["torch"]` — the harness runs in a venv where both are importable. |
| `compare` | adds `"close"` (float `allclose`) to the existing `"exact"`/`"unordered"`. numpy/torch outputs are compared by **shape + tolerance**, NaN/inf-safe. |
| `rtol`, `atol` | tolerances for `compare:"close"` (defaults `1e-4`, `1e-6`). |
| `reference` | a correct implementation (same signature as `entry_point`). Instead of hardcoding `expected`, the harness runs `reference` to compute it. |
| `random_tests` | `{count, shapes, dtype, range, seed[, mode]}` — property-based inputs. The harness seeds an RNG, generates inputs of the given `shapes`, runs `reference` for `expected`, runs the user, and compares. A `shapes` value that is an **int** is passed as a **constant scalar arg** (for `k`, sizes, …). `mode:"autograd"` switches to the torch-autograd checker. |
| `banned` | tokens (names / attributes / dotted calls) rejected by an AST scan before execution — e.g. `["view","sum","reshape"]` — to force first-principles broadcasting (Tensor-Puzzles). |

Static `tests` still work for coding problems; ML problems use `reference` + `random_tests` instead.

## How the harness runs an ML problem

`app/executor.py` runs user code in a subprocess (timeout-isolated) via one of three runners, chosen in
`app/main.py`'s `/submit` dispatch:

- **`run_reference_tests`** — `reference` + `random_tests` present. Generate inputs, run reference for
  expected, run user, `close`-compare; report per-case shapes + max-abs-error on failure.
- **`run_autograd_tests`** — `random_tests.mode == "autograd"`. `reference` is a `forward(x)`; generate a
  random `x` (requires_grad) and upstream grad `g`, compute the true gradient with
  `torch.autograd.grad`, and compare the user's `entry_point(x, g)` to it.
- **`run_tests`** — the classic static-`tests` path (all coding problems).

A `banned` list short-circuits (with a message naming the token) before any code runs.

## Authoring a new ML drill

1. Copy the template below into `problems/<slug>.json`.
2. Write `reference` (correct) and `starter_code` (a `# TODO` stub). Put the correct implementation in
   `solutions[-1].code` too (it must agree with `reference` over the random tests).
3. State the math in the `description` with LaTeX (`$inline$`, `$$block$$`) and give input/output shapes.
4. Pick `concepts` from the canonical list (see `app/tags.py CANONICAL_TAGS`).
5. Validate: `uv run pytest tests/test_problems_valid.py -k <slug>` — the reference must pass its own
   random tests. (`test_problems_valid.py` runs this for every problem in CI.)

### Template (numpy, `close`)
```json
{
  "slug": "softmax-stable",
  "track": "ml",
  "source": "ML-Impl",
  "title": "Numerically Stable Softmax",
  "difficulty": "Easy",
  "concepts": ["activations", "numerical-stability"],
  "libraries": ["numpy"],
  "description": "Implement softmax over the last axis: $\\text{softmax}(x)_i = \\dfrac{e^{x_i}}{\\sum_j e^{x_j}}$.\n\nSubtract the row max before exponentiating for numerical stability. Input `x` has shape `(n, d)`; return shape `(n, d)`.",
  "entry_point": "softmax",
  "starter_code": "import numpy as np\n\ndef softmax(x):\n    # TODO\n    pass\n",
  "compare": "close",
  "rtol": 1e-5, "atol": 1e-8,
  "reference": "import numpy as np\n\ndef softmax(x):\n    x = x - x.max(axis=-1, keepdims=True)\n    e = np.exp(x)\n    return e / e.sum(axis=-1, keepdims=True)\n",
  "random_tests": {"count": 20, "shapes": {"x": [8, 5]}, "dtype": "float32", "range": [-5, 5], "seed": 0},
  "hints": ["Subtract max along axis=-1 before exp.", "keepdims=True keeps broadcasting clean."],
  "solutions": [{"name": "Stable softmax", "explanation": "Shift by the row max, exponentiate, normalize.", "code": "def softmax(x):\n    x = x - x.max(axis=-1, keepdims=True)\n    e = np.exp(x)\n    return e / e.sum(axis=-1, keepdims=True)\n", "complexity": "O(n*d)"}]
}
```

### torch autodiff variant
Set `libraries:["torch"]`, `reference` to `def forward(x): return <f(x)>`, `entry_point` to
`<op>_backward(x, g)` (returns `dx`), and `random_tests` with `"mode":"autograd"`. The checker verifies
your gradient against `torch.autograd`.

## A note on the input harness

`random_tests` applies one `dtype`/`range` to all generated arrays in a problem, and a `shapes` value that
is an int is passed as a constant scalar. Problems that need genuinely mixed input types are modeled
around that (e.g. small integer feature ranges, or constants baked into the reference). If you add a
drill that needs richer input generation, extend `_gen_inputs` in `app/executor.py`.
