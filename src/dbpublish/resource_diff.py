from typing import Union


class ResourceDiff:
    def __init__(self, repo_dir, original_resource: str, latest_resource: str, resources_folder: str = "Resources"):

        self.repo_dir = repo_dir

        self.latest_resource = latest_resource
        self.original_resource = original_resource

        self.latest_dir =   f"{repo_dir}/{resources_folder}/{latest_resource}"
        self.original_dir = f"{repo_dir}/{resources_folder}/{original_resource}"

        self.files_a = None
        self.files_b = None
        self.all_files = None

    def compare(self):
        import os

        self.files_a = [os.path.join(dp, f) for dp, dn, filenames in os.walk(self.original_dir) for f in filenames]
        self.files_a = [r[len(self.original_dir) + 1:] for r in self.files_a]

        self.files_b = [os.path.join(dp, f) for dp, dn, filenames in os.walk(self.latest_dir) for f in filenames]
        self.files_b = [r[len(self.latest_dir) + 1:] for r in self.files_b]

        self.all_files = []
        self.all_files.extend(self.files_a)
        self.all_files.extend(self.files_b)

        html = f"""<!DOCTYPE html><html>
        <head>
        <style>
            td {{padding: 5px; border:1px solid silver}}
        </style>
        </head>
        <body style="font-size:16px">
            <p>Original: <b>{self.original_resource}</b></p>
            <p>Latest: <b>{self.latest_resource}</b></p>
            <table style="border-collapse: collapse; border-spacing:0">"""

        html += f"""<thead><tr><td>Change Type</td><td>Message</td></tr></thead>"""

        for file in self.all_files:
            sd = SegmentDiff(file, self.original_dir, self.latest_dir)
            sd.read_segments()
            html += f"""<tbody><tr><td colspan="2" style="background-color:gainsboro">/{sd.name}</td></tr>"""

            for change in sd.diff():
                html += f"""<tr><td style="white-space:nowrap">{change.change_type}</td>
                                <td>{change.message}</td>
                            </tr>"""
                if change.change_type == "Cell Changed":
                    html += f"""<tr><td style="overflow:scroll; white-space:pre" colsapn="2">
                        <table><tr><td>{change.original_text}</td><td>{change.latest_text}</td></tr></table>
                    </td></tr>"""

            html += f"""</tbody>"""

        html += "</table></body></html>"
        return html


class Change:
    def __init__(self, change_type: str, name: str, message: str, original_text: str = None, latest_text: str = None):
        self.change_type = change_type
        self.name = name
        self.message = message

        self.original_text = original_text
        while "\n\n" in self.original_text:
            self.original_text = self.original_text.replace("\n\n", "\n")

        self.latest_text = latest_text
        while "\n\n" in self.latest_text:
            self.latest_text = self.latest_text.replace("\n\n", "\n")


class Segment:
    def __init__(self, guid):
        self.guid = guid
        self.contents = ""

    def add_line(self, line):
        self.contents += line


class SegmentDiff:

    def __init__(self, name, original_dir, latest_dir):
        self.name = name
        self.original_dir = original_dir
        self.latest_dir = latest_dir
        self.segments_a = None
        self.segments_b = None

    def diff(self):
        if self.segments_a is None:
            return [Change("Missing Notebook", self.name, f"{self.name} from original")]
        elif self.segments_b is None:
            return [Change("Missing Notebook", self.name, f"{self.name} from latest")]

        changes = []

        guids = list()
        guids.extend(self.segments_a.keys())
        guids.extend(self.segments_b.keys())
        guids = list(set(guids))

        for guid in guids:
            if guid not in self.segments_a:
                changes.append(Change("Cell Added", self.name, guid))
            elif guid not in self.segments_b:
                changes.append(Change("Cell Removed", self.name, guid))
            elif self.segments_a[guid].contents.strip() != self.segments_b[guid].contents.strip():
                # Try to figure out the first line that changed.
                changes.append(Change("Cell Changed", self.name, f"{guid}", self.segments_a[guid].contents.strip(), self.segments_b[guid].contents.strip()))

        return changes

    def read_segments(self):
        self.segments_a = self._read_segments_file(f"{self.original_dir}/{self.name}")
        self.segments_b = self._read_segments_file(f"{self.latest_dir}/{self.name}")

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
