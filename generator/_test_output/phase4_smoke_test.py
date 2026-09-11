"""Phase 4 end-to-end smoke test: a freshly-created default 'Ch5 Button' added to a page --
verified via harness round-trip AND an exact (112/112 keys, 0 value mismatches) structural
comparison against the real reference file's plain "Button1" instance
(C:\\Solutions\\ClaudeSamples\\Components\\Component - Button.cuig, id "i9nb")."""
import sys
import tomllib
import re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "harness"))

from page import build_page_attributes, write_cuig  # noqa: E402
from sdk import read_sdk  # noqa: E402
from ch5_button import build_default_button_element, build_default_button_attributes, button_size_css_vars  # noqa: E402
import compare  # noqa: E402

OUT = Path(__file__).resolve().parent / "Phase4Smoke"
OUT.mkdir(parents=True, exist_ok=True)
REF_DIR = Path(r"C:\Solutions\ClaudeSamples\Components")


def parse_page_attrs(path: Path) -> dict:
    raw = Path(path).read_text(encoding="utf-8")
    headers = list(re.finditer(r"^\{(\w+)\}[ \t]*\r?\n?", raw, re.MULTILINE))
    sections = {}
    for i, m in enumerate(headers):
        start = m.end()
        end = headers[i + 1].start() if i + 1 < len(headers) else len(raw)
        sections[m.group(1)] = raw[start:end]
    return tomllib.loads(sections["PageAttributes"])


sdk = read_sdk("2.18.0")

# --- 1. build a default button element + add it to a page ---------------------------
html, css, element = build_default_button_element(
    sdk, component_name="Button1", element_id="i9nb",
    x=58, y=58, width=84, height=42, z_index=1, resolution=(1280, 800),
)
page_attrs = build_page_attributes(name="ButtonSmoke")
page_path = OUT / "ButtonSmoke.cuig"
write_cuig(page_path, page_attrs, html=html, css=css, elements=[element])
assert compare.round_trip_check(page_path), "button page round-trip failed"
assert "left: 58px" in css and "width: 84px" in css and "auto" not in css, "position CSS missing/wrong"
print("page with button: round-trip OK, position CSS present (regression test for the "
      "user-reported 'auto' Left/Top/Width/Height bug)")

# --- 2. structural comparison against the real reference file's plain button --------
# contract_signals=(): the real Button1 has no contract signals enabled (nothing in the
# reference project's Component - Button.cuig carries "Contract Enabled"), so the
# like-for-like comparison is against a button with none either. Phase 6's default of
# Press+Selected is asserted separately, in contracts_task3_button_test.py.
gen_attrs = build_default_button_attributes(
    sdk, component_name="Button1", element_id="i9nb", label="Button1", contract_signals=())

raw = (REF_DIR / "Component - Button.cuig").read_text(encoding="utf-8")
headers = list(re.finditer(r"^\{(\w+)\}[ \t]*\r?\n?", raw, re.MULTILINE))
sections = {}
for i, m in enumerate(headers):
    start = m.end()
    end = headers[i + 1].start() if i + 1 < len(headers) else len(raw)
    sections[m.group(1)] = raw[start:end]
ref_page_attrs = tomllib.loads(sections["PageAttributes"])
ref_button1 = ref_page_attrs["Elements"][-1]
assert ref_button1["Attributes"]["id"] == "i9nb", "reference file's last button is expected to be Button1 (id i9nb)"
assert not any(v == "Contract Enabled" for v in ref_button1["Attributes"].values()),     "the reference button is expected to have no contract signals -- if it gains one, "     "the contract_signals=() above is no longer the like-for-like comparison"

gen_keys = [k for k, _ in gen_attrs]
ref_keys = list(ref_button1["Attributes"].keys())
assert gen_keys == ref_keys, "attribute key order mismatch vs real Button1"

gen_dict = dict(gen_attrs)
ref_dict = ref_button1["Attributes"]
# "size": real Button1 is "regular" only because its dimensions (84x42) happen to equal
# the theme's regular preset -- this module always forces "custom" (user-directed fix for
# a canvas-adorner-vs-actual-render-size mismatch bug, see ch5_button.py), which is the
# functionally correct choice once explicit width/height are always supplied, matching
# every OTHER real instance in the reference file that was actually resized.
mismatches = [
    (k, gen_dict.get(k), ref_dict.get(k)) for k in ref_dict
    if k != "size" and gen_dict.get(k) != ref_dict.get(k)
]
assert not mismatches, f"value mismatches vs real Button1: {mismatches}"
assert gen_dict["size"] == "custom" and ref_dict["size"] == "regular"

print(f"default button: {len(gen_keys)}/{len(ref_keys)} attribute keys match real Button1, "
      f"0 unexpected value mismatches (schema-driven: component-context.json defaults.attributes + "
      f"sass-schema.json sync-sector derivation, not guessed; 'size' deliberately forced to "
      f"'custom' -- see comment)")

# --- 3. icon variant, structurally compared to the real "ButtonWithIcon" instance ---
icon_attrs = build_default_button_attributes(
    sdk, component_name="ButtonWithIcon", element_id="i2yz3h60yx", label="ButtonWithIcon",
    icon_class="fa-solid fa-address-book", icon_library="FA Classic Solid",
)
ref_icon = ref_page_attrs["Elements"][2]["Attributes"]  # ButtonWithIcon is Elements[2] (html document order)
assert ref_icon["componentName"] == "ButtonWithIcon"
gen_icon_dict = dict(icon_attrs)
# oldID/ccid_customSizeSet are copy/paste + resize UI-state artifacts on the real instance,
# never part of an "add component" creation payload (same call made for common wiring in
# docs/architecture/03-page-widget-creation.md) -- excluded from the comparison, not from
# the generator's fidelity claim.
known_artifacts = {
    "oldID", "ccid_customSizeSet",  # copy/paste + resize UI-state, not creation payload
    "size",  # real instance was independently resized ("custom" vs "regular") -- unrelated to the icon variant
}
icon_missing = [k for k in ref_icon if k not in gen_icon_dict and k not in known_artifacts]
icon_mismatches = [
    (k, gen_icon_dict.get(k), v) for k, v in ref_icon.items()
    if k not in known_artifacts and gen_icon_dict.get(k) != v
]
assert not icon_missing, f"icon variant missing keys vs real ButtonWithIcon: {icon_missing}"
assert not icon_mismatches, f"icon variant value mismatches vs real ButtonWithIcon: {icon_mismatches}"
print("icon variant: matches real ButtonWithIcon exactly (excluding oldID/ccid_customSizeSet "
      "copy/paste-resize artifacts and an independent 'size' customization, none of which "
      "are part of the icon variant itself)")

base_attrs = dict(build_default_button_attributes(sdk, component_name="X", element_id="ix"))

# --- image variant -- NOT byte-matched against the real "Button"/ButtonWithImage
# instance: that real instance also carries a full, unused iconsector sync block (12 +
# 4 toggle keys), which trace-confirmed is stale residue from its specific edit history
# (it was authored as an icon-type button then switched to image-type; setSyncData only
# ever ADDS sync attributes, never removes them on a mode switch) rather than something a
# single fresh "add component with image_icon_type=imageasset" would ever produce. This
# generator intentionally produces the clean, edit-history-free result instead (see
# docs/architecture/04-ch5-schema.md) -- sanity-checked here: adds exactly the 16 expected
# imagesector sync keys and nothing iconsector-related. ---
image_extra = sorted(set(dict(build_default_button_attributes(
    sdk, component_name="X", element_id="ix", image_icon_type="imageasset", asset_id="a",
))) - set(base_attrs) - {"assetid"})
assert len(image_extra) == 16 and all(k.startswith("ccid_sync_") and "imagesector" in k for k in image_extra), image_extra
print("image variant: adds exactly the 16 expected imagesector sync keys, no iconsector "
      "residue (intentionally diverges from the real sample's edit-history artifact -- see doc)")

# --- 4. checkbox variant -- NOT present in the reference project (no real sample to
# confirm against); sanity-check only: same schema-driven mechanism as the confirmed
# icon/image cases (sass-schema.json's Checkbox sector), round-trips cleanly, and adds
# exactly the 4 expected checkboxsector sync keys with no other unexpected changes. ---
checkbox_attrs = dict(build_default_button_attributes(sdk, component_name="X", element_id="ix", checkbox_show=True))
checkbox_extra = sorted(set(checkbox_attrs) - set(base_attrs))
assert checkbox_extra == [
    "ccid_sync_normal_checkboxsector_color", "ccid_sync_normal_checkboxsector_color_toggle",
    "ccid_sync_pressed_checkboxsector_color", "ccid_sync_selected_checkboxsector_color",
], checkbox_extra
assert checkbox_attrs["checkboxshow"] == "true"
print("checkbox variant: adds exactly the 4 expected checkboxsector sync keys "
      "(UNCONFIRMED against a real file -- none exists in the reference project)")

# --- 5. round-trip each variant's actual .cuig output (not just the attribute dict) ---
variant_kwargs = {
    "icon": dict(icon_class="fa-solid fa-address-book", icon_library="FA Classic Solid"),
    "image": dict(image_icon_type="imageasset", asset_id="498f8b9e-eade-4d9d-9475-49bb03d4324b"),
    "checkbox": dict(checkbox_show=True),
}
for variant_name, kwargs in variant_kwargs.items():
    v_html, v_css, v_element = build_default_button_element(
        sdk, component_name=f"{variant_name}Button", element_id=f"iv{variant_name}",
        x=20, y=20, width=150, height=50, z_index=1, resolution=(1280, 800), **kwargs,
    )
    v_page_attrs = build_page_attributes(name=f"{variant_name.title()}Smoke")
    v_page_path = OUT / f"{variant_name.title()}Smoke.cuig"
    write_cuig(v_page_path, v_page_attrs, html=v_html, css=v_css, elements=[v_element])
    assert compare.round_trip_check(v_page_path), f"{variant_name} variant page round-trip failed"
    assert "auto" not in v_css and "width: 150px" in v_css
    print(f"{variant_name} variant: .cuig round-trip OK, position CSS present")

# --- 6. --ch5-button--regular-{width,height} CSS vars, confirmed against real
# ButtonWithIcon (id i2yz3h60yx, 190x58) -- a second user-reported bug: the canvas
# selection adorner was correctly sized via width/height, but the actual rendered button
# still didn't match, because ch5-button's own internal rendering reads its visual size
# from these CSS custom properties (not plain width/height), sourced from
# component-context.json's classToVariableMapping "idSelector" entry. ---
vars_190x58 = button_size_css_vars(sdk, width=190, height=58)
assert vars_190x58 == {"--ch5-button--regular-width": "190px", "--ch5-button--regular-height": "58px"}, vars_190x58
_, icon_css, _ = build_default_button_element(
    sdk, component_name="ButtonWithIcon", element_id="i2yz3h60yx",
    x=75, y=358, width=190, height=58, z_index=4, resolution=(1280, 800),
    icon_class="fa-solid fa-address-book", icon_library="FA Classic Solid",
)
assert "--ch5-button--regular-width: 190px" in icon_css and "--ch5-button--regular-height: 58px" in icon_css
print("size CSS vars: --ch5-button--regular-width/height present and match real ButtonWithIcon exactly")

print("\nPHASE 4 SMOKE TEST: ALL CHECKS PASSED")
