# Consumer CFG review

The intermediate run exited 0 with blocks=1 and instructions=0. It provides no negative evidence about this function.

In header_consumer_analysis.py, the outer loop executes done.add(va), then the inner loop immediately checks cur in done with cur==va and exits. Separate queued/visited block starts from decoded instruction addresses, or permit the first instruction of the current block. Require a nonempty entry block and decoded prologue matching candidate_capstone_review.json before reporting success. Keep CFG traversal within the containing executable region and account for 16/32-bit instruction sizes and JAL aliases.

The worker may still be correcting this intermediate result: poll the existing job rather than launching a duplicate.

## Follow-up review

The completed verifier now has nonempty evidence: 603 blocks and 6000 decoded instructions, with validated header comparisons and record stride. This corrects the earlier zero-instruction run. However, exactly 6000 instructions indicates a configured cap; the report itself says it has not reached fixpoint. Therefore CFG extent and claims about unseen table-field accesses are partial. Header validation and the cited local instruction sequences are useful evidence, but do not call this a complete function or complete record schema. Follow-up `gsp_header_consumer_followup_v1` is running in an isolated output directory to remove the cap and trace all record fields.
