"""Repair interface inconsistencies observed in the completed v14 traces."""
from pathlib import Path

EXTENSION_SOURCE = '''
# Keep the observation helpers but remove an artificial local-crop size error.
_area_guard = '    if (r1-r0)*(c1-c0) > 256:\\n        raise ValueError("crop is limited to 256 cells; select a smaller region")\\n'
assert HELPERS.count(_area_guard) == 1
HELPERS = HELPERS.replace(_area_guard, '')
GUIDE = GUIDE.replace('Maximum 256 cells; use for a specific local area.',
                      'Use for a specific local area; keep printed output compact.')
GUIDE += '\\nRaw current_frame.segmentation nodes also include the same inclusive bbox field.\\n'
_original_patch_sandbox = patch_sandbox

def patch_sandbox(source):
    source = _original_patch_sandbox(source)
    anchor = '                self._segmentation = segment_layer(self._grid, COLOR_CHARS)\\n'
    if source.count(anchor) != 1:
        raise ValueError('Expected one lazy frame-segmentation anchor')
    addition = (
        '                for node in self._segmentation.get("nodes", []):\\n'
        '                    boundary = node.get("boundary", [])\\n'
        '                    node["bbox"] = ([min(p[0] for p in boundary), min(p[1] for p in boundary),\\n'
        '                                     max(p[0] for p in boundary), max(p[1] for p in boundary)]\\n'
        '                                    if boundary else None)\\n'
    )
    source = source.replace(anchor, anchor + addition)
    ast.parse(source)
    return source
'''


def build_source():
    return Path(__file__).with_name("observation_tools.py").read_text(encoding="utf8") + "\n" + EXTENSION_SOURCE
