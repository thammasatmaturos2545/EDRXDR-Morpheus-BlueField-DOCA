# BlueField source inspection core v1

Step 4 adds an offline, transport-independent read verification core and synthetic tests.
No Kafka adapter, network CLI, source offset commit, producer, approval issuer or replay is included.

The core validates the frozen plan and evidence, queries partition metadata, checks
low/high offsets, fetches the exact coordinates, verifies original bytes SHA256,
and rechecks retention bounds after fetch. Missing topics, missing records (including
compaction gaps), tombstones, changed bytes, invalid positions and timeouts fail closed.
It returns metadata only and replay_authorized=false. No payload is written.

A trusted future adapter MUST verify the isolated broker identity and deployment,
disable automatic topic creation and offset commits, use group_id=None and explicit
assign/seek, return original bytes without decoding, bound each operation by the supplied
remaining timeout, and close without committing. The injected interface does not enforce
these transport settings. Deadline checks cannot kill an adapter that blocks internally.
The future executable needs both client timeouts and an external process deadline.
No genuine Kafka integration is claimed by these tests.

A successful inspection is only a point-in-time observation, not approval or authorization.
Before any future publish, validate the canonical operator journal decision, current
approval expiry, reread exact source bytes, and durably reserve intent. Never use this
metadata report as substitute source bytes or as an approval artifact. Missing historical
source must not be recreated under the old run identity. No payload correction is allowed.

## Observed historical source availability

User-supplied VM output on this task reports that topic
shadow-bluefield-quarantine-input-20261012t193307z does not exist (describe exit 1).
This is a reported observation, not a probe performed by this package. It does not
establish why the topic disappeared. The historical PASS report remains unchanged.
A fresh isolated fixture must have a new run identity and distinct evidence.

The BlueField service must stay inactive/dead/disabled. No driver/interface/GPU,
live bluefield-events, automated response or shared runtime changes are needed.
