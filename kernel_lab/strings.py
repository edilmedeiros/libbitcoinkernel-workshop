from dataclasses import dataclass


TUTORIAL_TITLE = "Bitcoin Validation Without a Node"

TUTORIAL_OVERVIEW = """
This workshop is about the validation boundaries exposed by libbitcoinkernel.

This workshop focuses on the core validation tasks exposed by libbitcoinkernel: parsing serialized Bitcoin data into kernel objects, performing context-free checks, verifying transactions with explicit previous-output context, and validating data against a full chainstate. These fundamentals form the building blocks of Bitcoin validation. If you are interested in the broader complexities of building a full node—such as networking, RPC interfaces, wallets, or mempool management—those topics are covered in other workshops.

All data used in the tutorial is pre-generated regtest fixture data committed under `data/`. You will start from raw block and transaction bytes, parse them into opaque libbitcoinkernel objects, run context-free block checks, verify a transaction input using explicitly supplied previous-output data, and then process blocks through a fresh chainstate while observing validation callbacks, missing-parent failures, and a reorganization.

The tutorial uses Python to keep the exercises short and inspectable, but the objective is not to teach a Python abstraction. The objective is to introduce the underlying libbitcoinkernel concepts well enough that you can later approach the bare C or C++ API, evaluate or use other language bindings, or even begin implementing bindings of your own.

The guided lessons are meant to orient you, not to hide the work. Each lesson explains the validation boundary being exercised, identifies the fixture files involved, and shows the primitive command to run. Run that primitive command yourself, inspect the output, and only then move to the next lesson.

By the end, you should be able to explain the difference between parsing, context-free validation, explicit-context script verification, and chainstate-backed validation, and understand how those layers map back to libbitcoinkernel’s core object model.
"""

TUTORIAL_HOWTO = """
Use the `tutorial` command as your map through the workshop. Start by inspecting the current lesson with:

```
$ kernel-lab tutorial
```

Each lesson will show the concept being introduced, the fixture files involved, and the primitive command you should run. The tutorial command itself does not replace the exercise; it tells you what to do next and what to pay attention to.

To navigate, use the `next` and `previous` actions:

```
$ kernel-lab tutorial next
$ kernel-lab tutorial previous
```

The program will remember where you stopped.
"""


@dataclass(frozen=True)
class TutorialLesson:
    """Static text for one tutorial lesson."""
    lesson_id: str
    title: str
    what: str
    files: tuple[str, ...]
    focus: str
    command: str
    look_for: str
    discussion: str


# LESSON 01
lesson01 = TutorialLesson(
    lesson_id="01",
    title="Parse raw transaction bytes",
    what="""
In this lesson, you start with a raw serialized Bitcoin transaction.

The fixture file contains transaction data as consensus-encoded bytes. At this
point, the transaction is not yet something we have interpreted, checked, or
validated. It is only a byte string loaded from the `data/` directory (just like we just received it from the network, if we were a node).

Your first task is to ask libbitcoinkernel to deserialize those bytes into a
transaction object.

In Python, this happens through:

```python
pbk.Transaction(raw)
```

This corresponds to creating a transaction handle from serialized
bytes in the libbitcoinkernel API using `btck_transaction_create`.

A parsed transaction is not necessarily a valid spend. Parsing only tells us
that the byte string can be decoded as a transaction. It does not tell us
whether the inputs spend existing coins, whether the signatures are valid,
whether the previous outputs are unspent, or whether the transaction appears in
the active chain.
""".strip(),
    files=(
        "data/tx/103-alice-pays-bob.hex",
    ),
    focus="""
Focus on the distinction between decoding a transaction and validating a
transaction.

A Bitcoin transaction spends previous outputs and creates new outputs. But from
the serialized transaction alone, libbitcoinkernel cannot know whether the
previous outputs actually exist in the UTXO set, whether they are still
unspent, or whether the input scripts and witnesses are valid for those
previous outputs.

This command is only about parsing and inspection.
""".strip(),
    command="`$ kernel-lab parse-tx data/tx/103-alice-pays-bob.hex`",
    look_for="""
When you run the command, look for a transaction summary.

The output should include:

  - the transaction id,
  - the locktime,
  - the number of inputs,
    - for each input, the outpoint it spends,
  - the number of outputs,
    - for each output, the amount and the scriptPubKey.

The input outpoint identifies a previous transaction output in the
format `previous_txid:vout`.

This tells you what the input claims to spend. It does not prove that the
previous output exists, is unspent, or can actually be spent by this
transaction.

The outputs describe new coins created by this transaction. Each output has an
amount and a scriptPubKey. For now, print the raw scriptPubKey. Later, this can
be extended with a helper that recognizes common script templates and renders
the corresponding Bitcoin address.

Do not interpret this command as a validation result. The transaction has been
parsed and inspected, not proven valid.
""".strip(),
    discussion="""
1. The current kernel-facing transaction input API exposes only part of what a
   transaction input contains. In particular, access to `scriptSig` and witness
   stack data has been discussed as an additional kernel API surface.

   Why might the first exposed API have focused on outpoints rather than on the
   full unlocking data?

   Consider at least two possible explanations:

     - the library may be trying to expose only the minimum object surface
       needed for validation-oriented applications;

     - `scriptSig` and witness access may be useful for some applications, but
       not necessary for the first layer of this tutorial, where we are only
       inspecting the transaction's basic structure.

   Then consider the opposite argument: if an application wants to inspect
   transaction inputs, why should it be forced to deserialize the raw
   transaction again outside libbitcoinkernel?

2. One concrete use case for exposing input witness data and `scriptSig` is
   wallet scanning for protocols such as silent payments, where applications may
   need public keys from transaction inputs.

   Does that use case feel like it belongs inside the kernel API, or is it
   already moving toward wallet/application-level functionality?

   There is no obvious answer. The useful question is where the boundary should
   be drawn.

3. Create or load a syntactically invalid transaction and observe how the
   binding reports the failure.

   For example, a simple starting fixture is a truncated transaction:

       data/tx-invalid/103-alice-pays-bob-truncated.hex

   This can be generated by taking the valid transaction fixture and removing
   the last byte. When you try to construct `pbk.Transaction(raw)`, the parser
   should fail before you can inspect inputs or outputs.

   Pay attention to the shape of the error:

     - Is it a Python exception?
     - What exception type is raised?
     - Does the message tell you where parsing failed?
     - Can you distinguish "invalid serialization" from "valid serialization
       but invalid spend"?

4. After observing the failure, ask what a good binding should expose here.

   Should transaction construction return `None`, raise an exception, or return
   a structured parse error?

   If you were implementing bindings for another language, what error shape
   would you want?
""".strip(),
)

# LESSON 02
lesson02 = TutorialLesson(
    lesson_id="02",
    title="Parse raw block bytes",
    what="""
In the previous lesson, you parsed a serialized transaction and inspected its
inputs, outputs, locktime, and txid. Now you move one level up: a serialized
Bitcoin block.

A block is also consensus-encoded byte data, but it has a different structure.
It contains a block header and a vector of transactions. The header commits to
the transaction list through the Merkle root, and links the block to its parent
through the previous block hash.

Your task in this lesson is to load a raw block fixture from the `data/`
directory, ask libbitcoinkernel to parse it into an opaque block object, and
print a summary of the block.

In Python, this happens through:

```python
pbk.Block(raw)
```

Conceptually, this corresponds to creating a block handle from serialized bytes
in the libbitcoinkernel API.

As in the transaction lesson, parsing is still not validation. If the block
parses, we know only that the byte string can be decoded as a block-shaped
consensus object. We do not yet know whether its proof of work is acceptable,
whether its Merkle root is correct, whether it connects to our current
chainstate, or whether its transactions spend valid coins.
""".strip(),
    files=(
        "data/blocks-main/102-fund-alice.hex",
    ),
    focus="""
Focus on the block as a container and commitment structure.

Compared with the transaction you inspected in Lesson 01, a block introduces
two new ideas:

  - the block header links this block to a previous block;
  - the Merkle root commits to the transactions contained in the block.

At this stage, you are only inspecting those fields. You are not yet checking
whether the header is valid, whether the Merkle root actually matches the
transaction list, or whether the block connects to chainstate.
""".strip(),
    command="`$ kernel-lab parse-block data/blocks-main/102-fund-alice.hex`",
    look_for="""
When you run the command, look for a block summary.

The output should include:

  - the block hash,
  - the previous block hash,
  - the Merkle root,
  - the timestamp,
  - the number of transactions,
  - and the txid of each transaction in the block.

The previous block hash tells you which block this block claims as its parent.
That does not prove the parent is known to your chainstate.

The Merkle root is a commitment to the transaction list. At this point, you are
only printing the Merkle root from the parsed block header. The next validation
lessons will check whether the transaction list actually matches that
commitment.

The transaction ids let you connect this lesson back to Lesson 01. One of the
transactions in this block should correspond to the transaction fixture you
already inspected, or to a closely related fixture from the same generated
regtest sequence.

Do not interpret this command as a block validation result. The block has been
parsed and inspected, not proven valid.
""".strip(),
    discussion="""
Discussion and investigation:

1. A transaction has inputs and outputs. A block has a header and transactions.
   Which parts of the block appear to be commitments, and which parts are
   payload?

2. The previous block hash is just a field in the header. What additional state
   would libbitcoinkernel need before it could decide whether that previous
   block is actually known?

3. The Merkle root is printed directly from the block header. Should a parser
   recompute and check the Merkle root automatically, or should that belong to
   a separate validation step?

   What are the advantages of keeping parsing and validation separate?

4. If you changed one byte inside one transaction but left the block header
   unchanged, what would you expect to happen?

   Would the block still parse?
   Would the block hash change?
   Would the Merkle root in the header change?
   Would context-free validation succeed?

5. The command prints all transaction ids in the block. For an application that
   wants to build an index, is parsing enough, or should it wait until the block
   has been validated against chainstate?
""".strip(),
)

# LESSON 03
lesson03 = TutorialLesson(
    lesson_id="03",
    title="Context-free block validation",
    what="""
In the previous lesson, you parsed a serialized block and inspected its header
and transaction list. Parsing told you that the bytes could be decoded as a
block-shaped consensus object.

But blocks are not meaningless objects, they have associated semantics. Now you
ask a stronger question: does the parsed block pass context-free block checks?

A context-free block check is a validation step that does not require a view of
the active chain or the UTXO set. The checker can inspect the block itself: its
header, its transaction list, its coinbase transaction, its Merkle commitment,
and optionally its proof of work.

In Python, this happens through

```python
    state = block.check(consensus_params, flags)
```

This corresponds to the libbitcoinkernel C API operation `btck_block_check`.

The important point is what this check does *not* know. It does not know whether
the previous block is known to your chainstate. It does not know whether the
transactions spend existing unspent outputs. It does not know whether this
block would become part of the active chain.

This lesson should test three cases:

  1. a valid block fixture;
  2. a mutated block whose transaction data no longer matches the Merkle root;
  3. optionally, a block whose proof of work is insufficient.

The mutated block is especially useful because it should still parse. The
failure happens only when you ask the checker to verify the block's internal
commitments.
""".strip(),
    files=(
        "data/blocks-main/102-fund-alice.hex",
        "data/blocks-invalid/102-bad-merkle.hex",
        "data/blocks-invalid/102-bad-pow.hex  # optional, if generated",
    ),
    focus="""
Focus on the difference between object construction and context-free checking.

A block can parse successfully and still fail context-free validation. In
particular, if the transaction data is mutated while the header is left
unchanged, the block may still be decodable, but the transaction list no longer
matches the Merkle root committed to by the header.

Also focus on what is absent: no UTXO set, no active chain, no block connection,
and no script validation against previous outputs.
""".strip(),
    command="""
`$ kernel-lab check-block data/blocks-main/102-fund-alice.hex`

`$ kernel-lab check-block data/blocks-invalid/102-bad-merkle.hex`

`$ kernel-lab check-block data/blocks-invalid/102-bad-pow.hex`
""".strip(),
    look_for="""
When you run the command on the valid block, look for a successful
context-free check.

The output should make clear that:

  - the block parsed successfully;
  - context-free block checking was run;
  - the validation state reports success.

When you run the command on the bad-Merkle block, look for a different shape:

  - the block still parses successfully;
  - context-free checking runs;
  - the validation state reports failure.

This is the important lesson. The mutated fixture is not merely invalid bytes.
It is a parseable block object that fails a validation rule.

If you have an insufficient-proof-of-work fixture, it should demonstrate a
different kind of context-free failure: the block may be structurally coherent,
and its Merkle root may match its transaction list, but the header does not
satisfy the proof-of-work target under the selected checking flags.

Do not interpret a successful context-free check as full block validity. The
block has not been connected to chainstate. Its transactions have not been
validated against the UTXO set. It has not been selected into the active chain.
""".strip(),
    discussion="""
Discussion and investigation:

1. Why should parsing and context-free checking be separate operations?

   Consider the bad-Merkle fixture. It is useful precisely because it can become
   a block object before validation rejects it. What would be lost if parsing
   tried to enforce every possible rule immediately?

2. The block hash is the hash of the block header. If you mutate transaction
   data but leave the header unchanged, should the block hash change?

   What about the Merkle-root check?

   This distinction is subtle but important: the header commits to the
   transaction list through the Merkle root, but the block hash itself is
   computed from the header.

3. Which checks can be performed using only the block itself?

   Try to classify these examples:

     - the block serialization is well-formed;
     - the Merkle root matches the transaction list;
     - the block header satisfies proof of work;
     - the previous block is known;
     - all transaction inputs spend existing UTXOs;
     - coinbase maturity is respected.

   Which are context-free, and which require chainstate?

4. The command may expose checking flags. If proof-of-work and Merkle-root
   checks can be toggled, what should the default be for a teaching tool?

   Should `kernel-lab check-block` run all available context-free checks by
   default, or should it allow students to isolate individual checks?

5. If you do not yet have a bad-PoW fixture, create one.

   A possible strategy is to mutate the nonce or another header field while
   preserving a parseable block. Then run the checker with proof-of-work
   checking enabled.

   What changes?

     - Does the block still parse?
     - Does the block hash change?
     - Does the Merkle root still match?
     - Which validation result is reported?
""".strip(),
)

# LESSON 04
lesson04 = TutorialLesson(
    lesson_id="04",
    title="Verify a transaction input with explicit context",
    what="""
In the previous lessons, you saw that blocks can be parsed and then checked
using information contained in the block itself. A block header contains a
Merkle root, and the block contains the transaction list that should match that
commitment. That makes some block checks context-free.

Transactions are different.

A transaction is not a meaningless byte string. It has clear semantics: it
claims to spend previous outputs and create new outputs. But the transaction
does not carry the full previous outputs it spends. Each input contains an
outpoint, which identifies a previous transaction output, but it does not
contain that previous output's amount or scriptPubKey.

That missing information matters.

To verify a transaction input, libbitcoinkernel must be given explicit context:

    - the spending transaction;
    - the input index being verified;
    - the previous output's amount;
    - the previous output's scriptPubKey;
    - the script verification flags.

In this lesson, you will verify the same transaction three times. The
transaction bytes do not change. Only the supplied previous-output context
changes.

First, you will verify the input using the correct amount and scriptPubKey.
Then you will verify the same input with the wrong amount. Finally, you will
verify it with an incompatible scriptPubKey.

The goal is to see that transaction validation is contextual. The transaction
has meaning, but part of that meaning refers to data outside the transaction
itself.
""".strip(),
    files=(
        "data/tx/103-alice-pays-bob.hex",
        "data/prevouts/103-input0-correct.json",
        "data/prevouts/103-input0-wrong-amount.json",
        "data/prevouts/103-input0-wrong-script.json",
    ),
    focus="""
Focus on the fact that the transaction is the same in all three cases.

The command does not mutate the transaction. It changes only the context
against which input 0 is verified.

This is the key idea:

    a transaction input does not spend "in general";
    it spends a specific previous output.

That previous output has an amount and a scriptPubKey. If either one is wrong,
the verification result can change.
""".strip(),
    command="""
`$ kernel-lab verify-input data/prevouts/103-input0-correct.json`

`$ kernel-lab verify-input data/prevouts/103-input0-wrong-amount.json`

`$ kernel-lab verify-input data/prevouts/103-input0-wrong-script.json`
""".strip(),
    look_for="""
Run the three commands and compare their outputs.

With the correct fixture, verification should succeed:
`data/prevouts/103-input0-correct.json`.

This fixture supplies the previous output amount and scriptPubKey that input 0
actually spends.

With the wrong-amount fixture, verification should fail:
`data/prevouts/103-input0-wrong-amount.json`.

The scriptPubKey is still the expected one, but the amount is wrong. For
SegWit-style signature verification, the previous output amount is part of the
signature-checking context. A one-satoshi difference is enough to make the
signature verification fail.

With the wrong-script fixture, verification should also fail:
`data/prevouts/103-input0-wrong-script.json`.

Here the amount may be plausible, but the previous output scriptPubKey is not
the contract this input was constructed to satisfy.

The important observation is that the transaction id and serialized transaction
are unchanged across all three runs. What changes is the supplied context.

Do not interpret this as full transaction validation. You are verifying one
input against one explicitly supplied previous-output contract. You are not yet
asking whether that previous output exists in the active chain, whether it is
unspent, or whether it is mature. Those are chainstate questions.
""".strip(),
    discussion="""
Discussion and investigation:

1. The transaction input contains an outpoint. It tells you which previous
   output the input claims to spend.

   Why does the transaction not simply include a full copy of that previous
   output?

   Consider both sides:

     - including the previous output would make local verification easier;
     - not including it avoids duplicating historical data inside every
       spending transaction.

2. In this lesson, you manually provide the previous output amount and
   scriptPubKey through a fixture file.

   In a real node, where would that information normally come from?

   What is the difference between giving the verifier a previous output
   manually and asking chainstate to validate a transaction as part of a block?

3. The wrong-amount case is intentionally provocative.

   At first glance, an amount may look like accounting data rather than script
   data. But for SegWit signature verification, the spent amount is part of the
   message being checked.

   What would go wrong if signatures did not commit to the amount of the output
   being spent?

4. The wrong-script case shows that an input is not merely proving knowledge of
   some private key. It is satisfying a specific previous-output contract.

   How does this change the common phrase "a transaction is signed"?

   What is actually being authorized?

5. This command verifies one input using context supplied by a JSON fixture.
   That is useful for teaching, but it is not a complete transaction validation
   engine.

   What additional checks would be needed before calling the whole transaction
   valid in a block?

   Consider:

     - whether each previous output exists;
     - whether each previous output is unspent;
     - whether coinbase maturity rules apply;
     - whether all inputs are verified;
     - whether the transaction is valid under the block's consensus context.
""".strip(),
)

# LESSON 05
lesson05 = TutorialLesson(
    lesson_id="05",
    title="Build a local chainstate",
    what="""
In the previous lessons, you worked with Bitcoin objects mostly in isolation.

You parsed transactions and blocks. You checked a block using context-free
rules. You verified one transaction input by manually supplying the previous
output context it needed.

Now you move to the stateful part of libbitcoinkernel: chainstate.

A chainstate is the library's local view of validated block history and the
UTXO set produced by that history. When you process blocks through chainstate,
libbitcoinkernel is no longer asking only whether a block is well-formed in
isolation. It is asking whether the block connects to the blocks it already
knows and whether applying that block produces a valid next state.

This lesson is intentionally a little bureaucratic. Before the interesting
transaction blocks can be processed, you must first process the first 101
regtest blocks. Those blocks create enough history for coinbase outputs to
become mature and spendable. They are not interesting by themselves, but they
are the context that makes the later transactions meaningful.

The sequence is:

  1. create a fresh chainstate;
  2. register validation callbacks;
  3. process the first 101 blocks in order;
  4. process block 102;
  5. try to process block 104 before block 103;
  6. observe that block 104 cannot connect to your local chain;
  7. process block 103;
  8. process block 104 again;
  9. observe that block 104 can now connect.

This is the first lesson where you are doing context-aware block validation.
The library checks not only the block's internal structure, but also whether it
fits into the current local chainstate.
""".strip(),
    files=(
        "data/blocks-prefix/001.hex",
        "data/blocks-prefix/...",
        "data/blocks-prefix/101.hex",
        "data/blocks-main/102-fund-alice.hex",
        "data/blocks-main/103-alice-pays-bob.hex",
        "data/blocks-main/104-bob-pays-carol.hex",
    ),
    focus="""
Focus on two transitions.

First, focus on the transition from context-free checking to chainstate-backed
processing. A block that is structurally valid may still fail to connect if its
parent is missing from the local chainstate.

Second, focus on observability. The important information is not only the return
value of `process_block`. You should observe what the chainstate is doing
through validation callbacks, especially:

  - block_checked
  - block_connected

`block_checked` tells you that a block was checked and reports the validation
state seen by the kernel.

`block_connected` tells you that a block was actually connected to the active
chain and applied to the chainstate.

Block 104 is the teaching case. When you process it before block 103, it should
not connect. After block 103 is processed, the same block 104 should be able to
connect.
""".strip(),
    command="""
`$ kernel-lab chainstate-intro --kernel-datadir .kernel-lab/lesson-05`
""".strip(),
    look_for="""
When you run the command, look for the processing sequence.

You should see the tool create or reset a fresh kernel datadir, register
callbacks, and process the prefix blocks:

    data/blocks-prefix/001.hex
    ...
    data/blocks-prefix/101.hex

The output does not need to print every prefix block in detail. A summary is
enough:

    processed 101 prefix blocks

Then look for block 102 connecting successfully.

Next, look carefully at the attempt to process block 104 before block 103. The
block itself should still be parseable, and it may satisfy context-free checks,
but it should not connect to your local chainstate because its previous block is
missing.

Then block 103 should be processed and connected.

Finally, block 104 should be processed again. This time, because its parent is
known, it should be able to connect.

The important output to inspect is the callback stream. You should be able to
distinguish between:

  - a block being checked;
  - a block being connected;
  - a block failing to connect because its required context is missing.

A good output shape would look conceptually like this:

    [block_checked]    102 ... valid
    [block_connected]  102 ...

    [block_checked]    104 ... missing previous block
    # no block_connected event for 104 here

    [block_checked]    103 ... valid
    [block_connected]  103 ...

    [block_checked]    104 ... valid
    [block_connected]  104 ...

Do not treat this lesson as just setup. It is the first time libbitcoinkernel is
maintaining validation state for you.
""".strip(),
    discussion="""
Discussion and investigation:

1. This is the first lesson where libbitcoinkernel starts to look less like a
   collection of parsers and checkers and more like extracted Bitcoin Core
   machinery.

   What changed?

   In the previous lessons, you supplied isolated objects and explicit context.
   Here, the library maintains context across calls. Each processed block
   changes what the next block can validly do.

2. Block 104 is the central example.

   The bytes of block 104 do not change between the first and second attempt.
   Why does the result change?

   What did the chainstate learn after processing block 103?

3. The callback stream is part of the lesson.

   Why is `block_checked` not the same thing as `block_connected`?

   Can a block be checked without being connected?
   Can a block fail to connect for reasons that are not visible from the block
   bytes alone?

4. libbitcoinkernel inherits Bitcoin Core's model of context-aware validation.
   In that model, validating blocks means maintaining a local chainstate, and
   the chainstate includes a representation of the current UTXO set.

   This is powerful and conservative: it exposes the validation machinery used
   by Bitcoin Core. But it also means the library carries Bitcoin Core's view
   of what validation state looks like.

   Is that the right abstraction for every application?

5. Compare this with Utreexo-based projects such as Floresta and utreexod.

   A traditional Bitcoin Core-style node maintains a local database of the UTXO
   set. A Utreexo-style node instead works with a compact accumulator
   representation and proofs for the coins being spent.

   This changes the resource profile and the shape of validation. The node may
   not need to store the full UTXO set locally, but it must verify accumulator
   proofs as part of validation.

   What does that imply about libbitcoinkernel's current chainstate interface?

   Is the chainstate API a clean abstract validation interface, or is it more
   specifically an interface to Bitcoin Core's current validation architecture?

6. Suppose you wanted to build bindings for an application that only needs
   context-free block checks.

   Would you expose chainstate at all?

   Now suppose your application wants to validate blocks exactly the way Bitcoin
   Core does. How much of the chainstate machinery must become part of your
   binding?

7. The 101 prefix blocks are boring, but they are not optional.

   What consensus rule are they satisfying before the later transactions become
   useful?

   What does this tell you about historical context in Bitcoin validation?
""".strip(),
)

# LESSON 06
lesson06 = TutorialLesson(
    lesson_id="06",
    title="Observe a reorganization through callbacks",
    what="""
In the previous lesson, you created a fresh chainstate, processed blocks in
order, and observed that a block can only connect once its required context is
available.

Now you will use the same chainstate machinery to observe a reorganization.

A chainstate does not merely store a linear list of blocks. It maintains a block
tree: a set of known blocks that may form competing branches. At any moment, one
branch is selected as the active chain. If a competing branch with more work
appears, the active chain can change.

In this lesson, you will process a prepared regtest sequence with two competing
branches.

The sequence is:

  1. process the prefix blocks;
  2. process the common chain up to block 104;
  3. process branch A: blocks 105a and 106a;
  4. observe that branch A is the active chain;
  5. process branch B: blocks 105b, 106b, and 107b;
  6. observe the active chain reorganize to branch B.

Because this is regtest, each mined block has the same amount of work for our
purposes. The longer branch wins because it has more accumulated work.

The important part is not merely the final tip. The important part is the
callback stream. During the reorganization, blocks from the old active branch
are disconnected, and blocks from the new branch are connected.
""".strip(),
    files=(
        "data/blocks-prefix/001.hex",
        "data/blocks-prefix/...",
        "data/blocks-prefix/101.hex",
        "data/blocks-reorg/common/102-fund-alice.hex",
        "data/blocks-reorg/common/103-alice-pays-bob.hex",
        "data/blocks-reorg/common/104-bob-pays-carol.hex",
        "data/blocks-reorg/a/105a.hex",
        "data/blocks-reorg/a/106a.hex",
        "data/blocks-reorg/b/105b.hex",
        "data/blocks-reorg/b/106b.hex",
        "data/blocks-reorg/b/107b.hex",
        "data/meta/block-hashes.json",
    ),
    focus="""
Focus on the distinction between the block tree and the active chain.

A block can be known to the chainstate and still not be part of the active
chain. After the reorganization, the blocks from branch A should still be valid
known blocks, but they are no longer on the selected active chain.

Also focus on the callbacks:

  - `block_checked` tells you a block was checked;
  - `block_connected` tells you a block entered the active chain;
  - `block_disconnected` tells you a block left the active chain.

For applications that build indexes or maintain derived state, this distinction
is essential. If you update local state when blocks connect, you must also know
how to undo or update that state when blocks disconnect.
""".strip(),
    command="""
`$ kernel-lab reorg --kernel-datadir .kernel-lab/lesson-06`
""".strip(),
    look_for="""
When you run the command, look for three phases.

First, the tool should process the prefix blocks and the common chain:

    102-fund-alice
    103-alice-pays-bob
    104-bob-pays-carol

Then it should process branch A:

    105a
    106a

At this point, the active tip should be block 106a.

Next, the tool should process branch B:

    105b
    106b
    107b

Branch B has more accumulated work than branch A, so the active chain should
reorganize to branch B.

The callback stream should show the transition. Conceptually, you should see
something like:

    [block_connected]     105a
    [block_connected]     106a

    [block_checked]       105b
    [block_checked]       106b
    [block_checked]       107b

    [block_disconnected]  106a
    [block_disconnected]  105a

    [block_connected]     105b
    [block_connected]     106b
    [block_connected]     107b

The exact order and formatting may depend on the binding, but the conceptual
events should be visible: the old active branch is disconnected, and the new
branch is connected.

Finally, inspect the reported active tip. It should be the tip of branch B,
block 107b.

If the command also looks up branch A by hash through the block tree, observe
that stale branch blocks may remain known even though they are no longer part
of the active chain.

Do not interpret "stale" as "invalid." In this lesson, branch A contains valid
blocks. They are simply not on the active chain after branch B wins.
""".strip(),
    discussion="""
Discussion and investigation:

1. Before this lesson, it is tempting to think of validation as appending blocks
   to a list.

   Why is that mental model insufficient?

   What does the reorganization reveal about the difference between a block
   being known, a block being valid, and a block being active?

2. Branch A was active before branch B arrived. After branch B wins, branch A is
   no longer active.

   Did branch A become invalid?

   If not, what changed?

3. Suppose you are building an index of all transaction outputs in the active
   chain.

   If you update the index on `block_connected`, what must you do on
   `block_disconnected`?

   What bug would appear if your application ignored disconnection callbacks?

4. In this fixture, branch B wins because it is longer and, on regtest, each
   block contributes comparable work.

   In Bitcoin generally, what matters is not simply height, but accumulated
   work.

   Why is "longest chain" an imprecise phrase?

5. The callback interface exposes the chainstate as a sequence of events.

   Is that enough for an application to maintain its own derived state?

   What else might an application need: block data, undo data, block-tree entry
   lookup, or explicit active-chain queries?

6. A reorg is not an exceptional bug. It is part of the consensus model.

   How should this influence applications that present balances, confirmations,
   transaction histories, or indexes?

7. This lesson shows why libbitcoinkernel is more than a parser or a collection
   of stateless validation functions.

   Once chainstate is involved, the library is maintaining a local view of
   validated history.

   Is this still a small reusable library interface, or is it already exposing
   the architecture of Bitcoin Core?
""".strip(),
)

# TODO: (@edilmedeiros) add a lesson for logging before ingesting the blockchain. It will make
# it more clear what means to be a stateful library. The student should also
# be called to inspect the datadir that was created and see the chainstate database
# and blocksdir.

# TODO: (@edilmedeiros) add a lesson for exploring the orphan blocks that were left after the
# reorganization by using BlockTreeEntries.
TUTORIAL_LESSONS: tuple[TutorialLesson, ...] = (
    lesson01,
    lesson02,
    lesson03,
    lesson04,
    lesson05,
    lesson06,
)

