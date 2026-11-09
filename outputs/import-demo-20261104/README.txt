Synthetic CRM import samples. No real client data.
Each format contains four related sources: clients, services, specialists, appointments.
Upload each source with its matching entity type, then use suggested mapping.
References C100/S100/P100 link the appointment to the other rows.
Appointment: 14 December 2026,10:00 +05:00; confirmed;30 minutes.
Optional additional fields: category -> Loyalty(text), rating -> Rating(number), room -> Room(text).
The browser demo corrects client name to Transfer Client Edited before confirmation.
Phone is synthetic; use only in a disposable test business. Import alone must not send messages.
XLSX keeps timezone-bearing timestamp as explicit ISO text; numeric price/duration/rating are numbers.
