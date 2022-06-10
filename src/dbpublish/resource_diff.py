from typing import Union


class ResourceDiff:
    def __init__(self, dir_a: str, version_a: str, dir_b: str, version_b: str):
        self.dir_a = dir_a
        self.version_a = version_a
        self.dir_b = dir_b
        self.version_b = version_b

        self.files_a = None
        self.files_b = None
        self.all_files = None

    def compare(self):
        import os

        self.files_a = [os.path.join(dp, f) for dp, dn, filenames in os.walk(self.dir_a) for f in filenames]
        self.files_a = [r[len(self.dir_a) + 1:] for r in self.files_a]

        self.files_b = [os.path.join(dp, f) for dp, dn, filenames in os.walk(self.dir_b) for f in filenames]
        self.files_b = [r[len(self.dir_b) + 1:] for r in self.files_b]

        self.all_files = []
        self.all_files.extend(self.files_a)
        self.all_files.extend(self.files_b)

    def report(self):
        html = f"""<!DOCTYPE html><html>
        <head>
        <style>
            td {{padding: 5px; border:1px solid silver}}
        </style>
        </head>
        <body>
            <p>Dir A ({self.version_a}): <b>{self.dir_a}</b></p>
            <p>Dir B ({self.version_b}): <b>{self.dir_b}</b></p>
            <table style="border-collapse: collapse; border-spacing:0">"""

        html += f"""<thead><tr><td>Change Type</td><td>Message</td></tr></thead>"""

        for file in self.all_files:
            sd = SegmentDiff(file, self.dir_a, self.dir_b)
            sd.read_segments()
            html += f"""<tbody><tr><td colspan="2" style="background-color:gainsboro">/{sd.name}</td></tr>"""

            for change in sd.diff():
                html += f"""<tr><td style="white-space:nowrap">{change.change_type}</td>
                                <td>{change.message}</td></tr>"""
            html += f"""</tbody>"""

        html += "</table></body></html>"
        return html


class Change:
    def __init__(self, change_type, name, message):
        self.change_type = change_type
        self.name = name
        self.message = message


class Segment:
    def __init__(self, guid):
        self.guid = guid
        self.contents = ""

    def add_line(self, line):
        self.contents += line


class SegmentDiff:

    def __init__(self, name, dir_a, dir_b):
        self.name = name
        self.dir_a = dir_a
        self.dir_b = dir_b
        self.segments_a = None
        self.segments_b = None

    def diff(self):
        if self.segments_a is None:
            return [Change("Missing Notebook", self.name, f"{self.name} from directory A")]
        elif self.segments_b is None:
            return [Change("Missing Notebook", self.name, f"{self.name} from directory B")]

        changes = []

        guids = list()
        guids.extend(self.segments_a.keys())
        guids.extend(self.segments_b.keys())
        guids = list(set(guids))

        for guid in guids:
            if guid not in self.segments_a:
                changes.append(Change("Missing Cell", self.name, f"{guid} from directory A"))
            elif guid not in self.segments_b:
                changes.append(Change("Missing Cell", self.name, f"{guid} from directory B"))
            elif self.segments_a[guid].contents != self.segments_b[guid].contents:
                changes.append(Change("Cell Changed", self.name, f"{guid}"))

        return changes

    def read_segments(self):
        self.segments_a = self._read_segments_file(f"{self.dir_a}/{self.name}")
        self.segments_b = self._read_segments_file(f"{self.dir_b}/{self.name}")

    @staticmethod
    def _read_segments_file(file: str) -> Union[None, dict]:
        import os

        if not os.path.exists(file):
            return None

        with open(file, "r") as f:
            lines = f.readlines()

            segment = None
            segments = {}

            for i, line in enumerate(lines):
                try:
                    if i == 0:
                        pass  # Line zero will be the file name.

                    elif line.startswith("<hr>--i18n-"):
                        guid = line[11:].strip()
                        segment = Segment(guid)
                        segments[guid] = segment

                    elif line.startswith("<hr sandbox>--i18n-"):
                        guid = line[19:].strip()
                        segment = Segment(guid)
                        segments[guid] = segment

                    else:
                        segment.add_line(line)

                except Exception as e:
                    segment_num = len(segments)
                    raise Exception(f"Exception processing segment {segment_num}, line {i + 1} from {file}:\n{line}") from e

            return segments
