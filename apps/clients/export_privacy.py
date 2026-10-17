"""Redact a stored client CSV at download time without materializing the file."""
import csv
import io

from django.http import StreamingHttpResponse


def private_notes_redacted_csv(result_file):
    def rows():
        with result_file.open("rb") as source:
            with io.TextIOWrapper(source, encoding="utf-8-sig", newline="") as text:
                reader = csv.reader(text)
                header = next(reader, [])
                hidden = [index for index, name in enumerate(header) if name == "notes"]
                buffer = io.StringIO(newline="")
                writer = csv.writer(buffer)
                writer.writerow(header)
                yield buffer.getvalue()
                for row in reader:
                    for index in hidden:
                        if index < len(row):
                            row[index] = ""
                    buffer.seek(0)
                    buffer.truncate(0)
                    writer.writerow(row)
                    yield buffer.getvalue()

    response = StreamingHttpResponse(rows(), content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="clients.csv"'
    return response
