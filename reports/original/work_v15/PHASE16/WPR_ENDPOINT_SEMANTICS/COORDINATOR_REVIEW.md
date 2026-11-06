# Endpoint evidence review

Checked actual source ctrl2080fb.h lines3068-3093 and tu102/dev_fb.h lines39-44. API documentation explicitly describes wpr2End as exclusive (with a WPR1 copy/paste typo in description). Register header establishes bitfield/alignment but does not state HI endpoint convention. Missing implementation prevents proving raw HI maps directly to the API endpoint without adjustment. Accept API-contract evidence; hardware HI exclusivity remains unproven. Numerical decoded endpoint difference remains128.875MiB; allocation size and Reserved overlap retain this boundary caveat. Cross-generation register shapes and generic exclusive-range macros add no direct TU106 endpoint proof.

Machine JSON has duplicate `lines` and `excerpt` keys in the dev_fb evidence object, so a normal JSON parser retains only the HI entry. Use source/report directly for both LO/HI citations until schema is corrected.
