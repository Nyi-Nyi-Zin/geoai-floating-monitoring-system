# Field-observation evidence protocol

## Purpose

Field observations can supply independent evidence for later prospective validation of DeltaWatch’s monitoring records. A submitted observation is **not** a flood alert, a verified model label, or an automatically accepted ground-truth value.

## Required submission evidence

Each authenticated contributor must supply an observation time, latitude, longitude, and an impact class. A water-depth estimate, location-accuracy estimate, photo, and concise field note are optional but strongly encouraged. The application stores submitted photos in managed object storage and stores only the storage reference in the database.

| Field | Required | Validation use |
|---|---:|---|
| Observation time | Yes | Matches evidence to prospective target date |
| Latitude and longitude | Yes | Links evidence to a v7 grid cell or local area |
| Impact class | Yes | Describes observed flood condition, access impact, or absence of flooding |
| Water depth | No | Supports severity review; never inferred when absent |
| Accuracy estimate | No | Indicates location uncertainty |
| Photo | No | Reviewable visual evidence; not a model input until verified |
| Notes | No | Context only; not automatically parsed as a label |

## Access and review

Only authenticated users may submit observations. New entries receive `submitted` status. Only an administrator may change the status to `verified` or `rejected`, and the review action records reviewer identity, time, and a rationale. The public dashboard may show aggregate verified counts only; raw reporter identity, precise location, notes, and image links remain protected.

> No submitted or verified observation enables public warning delivery. A future validation study must pre-specify the spatial matching rule, time window, exclusion criteria, and performance metrics before field evidence is used to assess a model.
