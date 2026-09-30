# Deadline precision

The four timeline fields (`abstract_deadline`, `deadline`, `rebuttal_deadline`, and
`decision_deadline`) accept these backward-compatible representations:

- `"2027-02-28 17:00:00"`: a published clock time in the edition's documented timezone
- `"2027-02-28"`: a published calendar date with **unknown clock time**
- `TBD`: no published calendar date

Quote bare dates in YAML so they remain strings in generated JSON. Keep a
source-documented timezone such as `AoE`, `PT`, or `UTC+8` for date-only values.
Use `timezone: Unknown` only when the source does not state a zone. `Unknown`
cannot accompany a precise timestamp. Never replace missing information with
midnight, 23:59:59, UTC, AoE, or a historical estimate.

A date remains pending throughout its source calendar day. With an unknown zone,
it expires only after that date has passed everywhere (the end of the UTC-12
calendar day). Pending does **not** guarantee submissions are still open: the
clock time is unknown and users must check the official website. Sorting uses
calendar-day lower bounds internally, not an asserted deadline instant. Unknown
zone bounds span UTC+14 through UTC-12. Mixed rounds consider each valid node;
an old date-only round cannot hide a later future precise or date-only round.
A current/future edition with an unresolved last paper round stays TBD after
earlier known nodes pass; those known nodes do not seed estimates for that round.

The UI displays the published date and uncertainty without a seconds countdown
or an invented position on the precise-time graph. Favorites and conference
details list date-only nodes separately. Official date-only nodes never trigger
historical-date estimates. Precise and TBD behavior remains supported.

## Exports and consumers

- Conference JSON preserves original strings and the source timezone
- iCalendar and Google Calendar use all-day dates, with an exclusive next-day
  end; no UTC or TZID timestamp is invented for those events
- RSS includes the published date and uncertainty in text and omits `pubDate`
  for date-only items (a deadline date is not a known publication timestamp)
- Reminder JSON uses `precision: "date"`, `deadline_date: "YYYY-MM-DD"`,
  `deadline_at: null`, and the source `timezone`; precise entries retain their
  timestamp and use `precision: "datetime"`
- Email reminders preserve the source date/zone, state that the time is unknown,
  and classify days in the source zone (UTC-12 conservatively for Unknown)
- MCP date-only nodes have `precision: "date"`, `deadline_date`, and
  `utc_time: null`. Upcoming queries use calendar-day overlap rather than inventing
  an instant. TBD has unknown precision and no instant
- CLI output retains date-only values and identifies the unknown clock; ordering
  and filtering use calendar precision instead of datetime coercion

This support does not migrate conference records automatically. Each data change
still needs an official source for its date, stage, and timezone qualifications.
