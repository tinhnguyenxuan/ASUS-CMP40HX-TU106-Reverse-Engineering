# Coordinator review

Independently read raw ROM: corrected gap[0] is[0x28822,0x28832),16bytes; old118byte span improperly included102byte BIT entry array. Raw gap bytes agree with report.

PERFORMANCE v60 remains opaque because no applicable schema/consumer branch was established. Nonzero bytes after a proposed extent do not independently disprove that extent: adjacent tables/data may be nonzero. Do not use that negative argument as proof; absence of a justified v60 schema is the relevant gap. Conditional parsing tied to BIOS major version requires validating that version/precondition before adoption. No claim of full VBIOS decoding accepted.
