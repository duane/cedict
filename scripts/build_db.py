#!/usr/bin/env python3

import re
import sqlite3
import conversion

READING_RE = re.compile(r"U\+([A-F0-9]{4,8})\t(\w+)\t(.*)", re.U)
DICTIONARY_LIKE_RE = re.compile(r"U\+([A-F0-9]{4,8})\t(\w+)\t(.*)", re.U)
CEDICT_RE = re.compile(r"(.*?) (.*?) \[(.+)\] /(.*?)/", re.U)
# (:?\t\^(.*?)\$\(([GJKPMSTUBVXZC023]+)\))
IDS_RE = re.compile(r"U\+([A-F0-9]{4,8})\t\w\t(.*)")
IDS_STROKE_SEQUENCE_RE = re.compile(r"\^([^$]+)\$(?:\(([GHJKPMSTUBVXZC023]+)\))?")
IDS_ASTERISK_OPERATOR_RE = re.compile(
    r"\*U\+([A-F0-9]{4,8})(?:\(([GHJKPMSTUBVXZC023]+)\))?([=≡≠])U\+([A-F0-9]{4,8})"
)
IDS_ASTERIKS_COMMENTARY_RE = re.compile(r"\*(.+)")

VARIANT_RE = re.compile(
    r"U\+([A-F0-9]{4,8})\t(kSemanticVariant|kSimplifiedVariant|kSpecializedSemanticVariant|kSpoofingVariant|kTraditionalVariant|kZVariant)\t(.*)"
)
VARIANT_CODEPOINT_RE = re.compile("U\+([A-F0-9]{4,8})(?:<(.*))?")

READINGS_FIELDS_BY_FIELD_NAME = {
    "kCantonese": "cantonese",
    "kDefinition": "definition",
    "kHangul": "hangul",
    "kHanyuPinlu": "hanyu_pinlu",
    "kHanyuPinyin": "hanyu_pinyin",
    "kJapaneseKun": "japanese_kun",
    "kJapaneseOn": "japanese_on",
    "kKorean": "korean",
    "kMandarin": "mandarin",
    "kTang": "tang",
    "kTGHZ2013": "tghz2013",
    "kVietnamese": "vietnamese",
    "kXHC1983": "xhc1983",
}

DICTIONARY_LIKE_CONVERSION_BY_FIELD_NAME = {
    "kAlternateTotalStrokes": str,
    "kCangjie": str,
    "kCheungBauer": str,
    "kFenn": str,
    "kFourCornerCode": str,
    "kFrequency": int,
    "kGradeLevel": int,
    "kHDZRadBreak": str,
    "kHKGlyph": str,
    "kPhonetic": str,
    "kStrange": str,
    "kUnihanCore2020": str,
}

DICTIONARY_LIKE_FIELDS_BY_FIELD_NAME = {
    "kAlternateTotalStrokes": "alternate_total_strokes",
    "kCangjie": "cangjie",
    "kCheungBauer": "cheung_bauer",
    "kFenn": "fenn",
    "kFourCornerCode": "four_corner_code",
    "kFrequency": "frequency",
    "kGradeLevel": "grade_level",
    "kHDZRadBreak": "hdz_rad_break",
    "kHKGlyph": "hk_glyph",
    "kPhonetic": "phonetic",
    "kStrange": "strange",
    "kUnihanCore2020": "unihan_core_2020",
}

IDS_FIELDS_BY_FIELD_LETTER = {
    "G": "source_china",
    "J": "source_japan",
    "K": "source_korea",
    "P": "source_dpr_korea",
    "M": "source_macau",
    "S": "source_sat",
    "t": "source_taiwan",
    "u": "source_unicode",
    "b": "source_uk",
    "v": "source_vietnam",
    "UCS2003": "source_ucs2003",
    "x": "source_x",
    "z": "source_z",
}


def create_schema(sql):
    cursor = sql.cursor()
    cursor.execute(
        """CREATE TABLE IF NOT EXISTS hsk (
            entry text primary key,
            hsk_2012_level integer,
            hsk_2023_level integer
        );"""
    )
    cursor.execute(
        """CREATE TABLE IF NOT EXISTS variants (
            codepoint integer NOT NULL,
            variant_type text NOT NULL,
            variant_codepoint integer NOT NULL
        );"""
    )
    cursor.execute(
        """CREATE TABLE IF NOT EXISTS semantic_variants (
            codepoint integer NOT NULL,
            variant_type text not null,
            source text,
            is_t bool not null default false,
            is_b bool not null default false,
            iz_z bool not null default false,
            is_f bool not null default false,
            is_j bool not null default false
        )"""
    )
    cursor.execute(
        """CREATE TABLE IF NOT EXISTS cedict (
            simplified_morpheme text not null,
            traditional_morpheme text not null,
            phonetic text not null,
            phonetic_pinyin text not null,
            english text not null
        );"""
    )

    cursor.execute(
        """CREATE TABLE IF NOT EXISTS readings (
            codepoint integer,
            textual text,
            cantonese text,
            definition text,
            hangul text,
            hanyu_pinyin text,
            hanyu_pinlu text,
            japanese_kun text,
            japanese_on text,
            korean text,
            mandarin text,
            tang text,
            tghz2013 text,
            vietnamese text,
            xhc1983 text
        );"""
    )

    cursor.execute(
        """CREATE TABLE IF NOT EXISTS dictionary_like (
        codepoint integer,
        alternate_total_strokes text,
        cangjie text,
        cheung_bauer text,
        fenn text,
        four_corner_code text,
        frequency integer,
        grade_level integer,
        hdz_rad_break text,
        hk_glyph text,
        phonetic text,
        strange text,
        unihan_core_2020 text,
        strange_is_asymmetric bool,
        strange_is_cursive bool,
        strange_is_unusual bool,
        strange_bopomofo integer,
        strange_is_fully_reflective bool,
        strange_fully_reflective integer,
        strange_is_mirrored bool,
        strange_mirrored integer,
        strange_is_odd bool,
        strange_odd integer,
        strange_is_rotated bool,
        strange_rotated integer,
        strange_hangul_component integer,
        strange_incomplete text,
        strange_katakana text,
        strange_stroke_heavy integer
    );"""
    )

    cursor.execute(
        """CREATE TABLE IF NOT EXISTS ids (
            codepoint integer primary key,
            source_china text,
            source_japan text,
            source_korea text,
            source_dpr_korea text,
            source_macau text,
            source_sat text,
            source_taiwan text,
            source_unicode text,
            source_uk text,
            source_vietnam text,
            source_ucs2003 text,
            source_x text,
            source_z text
        );"""
    )
    sql.commit()


def import_readings(sql):
    cursor = sql.cursor()
    reading_data_by_codepoint = {}

    with open("./assets/Unihan_Readings.txt") as f:
        for line in f.readlines():
            match = DICTIONARY_LIKE_RE.match(line)
            if match is not None:
                codepoint = int(match[1], 16)
                reading_data = reading_data_by_codepoint.get(codepoint) or {}
                field_name = match[2]
                field_value = match[3]
                reading_data[READINGS_FIELDS_BY_FIELD_NAME[field_name]] = field_value
                reading_data_by_codepoint[codepoint] = reading_data
            else:
                pass

    reading_data = [
        (
            codepoint,
            chr(codepoint),
            values.get("cantonese"),
            values.get("definition"),
            values.get("hangul"),
            values.get("hanyu_pinyin"),
            values.get("hanyu_pinlu"),
            values.get("japanese_kun"),
            values.get("japanese_on"),
            values.get("korean"),
            values.get("mandarin"),
            values.get("tang"),
            values.get("tghz2013"),
            values.get("vietnamese"),
            values.get("xhc1983"),
        )
        for (codepoint, values) in reading_data_by_codepoint.items()
    ]
    print("Writing %d reading rows to db" % (len(reading_data_by_codepoint),))
    cursor.executemany(
        "INSERT INTO readings VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        reading_data,
    )
    sql.commit()
    print("ok")


STRANGE_ACU_RE = re.compile(r"[ACU]")
STRANGE_BOPOMOFO_RE = re.compile(r"B:U\+(31[0-2AB][0-9A-F])")
STRANGE_FMOR_RE = re.compile(r"([FMOR])(?::U\+([23]?[0-9A-F]{4}))?")
STRANGE_HANGUL_RE = re.compile(r"H:U\+(31[3-8][0-9A-F])")

# matches but does not capture
STRANGE_INCOMPLETE_RE = re.compile(r"I:((?::?U\+[23]?[0-9A-F]{4})*)")
STRANGE_INCOMPLETE_CODEPOINT_RE = re.compile(r"U\+([23]?[0-9A-F]{4})")

STRANGE_KATAKANA_RE = re.compile(r"K(?::?(.+))")
STRANGE_KATAKANA_CODEPOINT_RE = re.compile(r"U\+(30[A-F][0-9A-F])")

STRANGE_STROKE_RE = re.compile(r"S:([4-9][0-9])")


def parse_strange(codepoint, kStrange):
    fields = kStrange.split(" ")
    is_asymmetric = False
    is_cursive = False
    is_unusual = False
    bopomofo = None
    is_fully_reflective = False
    fully_reflective = None
    is_mirrored = False
    mirrored = None
    is_odd = False
    odd = None
    is_rotated = False
    rotated = None
    hangul_component = None
    incomplete = ""
    katakana = ""
    stroke_heavy = None
    for field in fields:
        if field == "A":
            is_asymmetric = True
            continue
        if field == "C":
            is_cursive = True
            continue
        if field == "U":
            is_unusual = True
            continue

        bopomofo_match = STRANGE_BOPOMOFO_RE.match(field)
        if bopomofo_match is not None:
            bopomofo = int(bopomofo_match[1], 16)
            continue

        fmor_match = STRANGE_FMOR_RE.match(field)
        if fmor_match is not None:
            (fmor, id) = fmor_match.groups()
            if fmor == "F":
                is_fully_reflective = True
                if id is not None:
                    fully_reflective = int(id, 16)
            elif fmor == "M":
                is_mirrored = True
                if id is not None:
                    mirrored = int(id, 16)
            elif fmor == "O":
                is_odd = True
                if id is not None:
                    odd = int(id, 16)
            elif fmor == "R":
                is_rotated = True
                if id is not None:
                    rotated = int(id, 16)
            else:
                raise NotImplementedError("expected FMOR")
            continue

        hangul_match = STRANGE_HANGUL_RE.match(field)
        if hangul_match is not None:
            hangul_component = int(hangul_match[1], 16)
            continue

        if field == "I":
            incomplete = ""
            continue

        incomplete_match = STRANGE_INCOMPLETE_RE.match(field)
        if incomplete_match is not None:
            codepoints = incomplete_match[1].split(":")
            incomplete = "".join(
                chr(int(STRANGE_INCOMPLETE_CODEPOINT_RE.match(codepoint)[1], 16))
                for codepoint in codepoints
            )
            continue

        katakana_match = STRANGE_KATAKANA_RE.match(field)
        if katakana_match is not None:
            codepoints = katakana_match[1].split(":")
            katakana = "".join(
                chr(int(STRANGE_KATAKANA_CODEPOINT_RE.match(codepoint)[1], 16))
                for codepoint in codepoints
            )
            continue

        stroke_match = STRANGE_STROKE_RE.match(field)
        if stroke_match is not None:
            stroke_heavy = int(stroke_match[1])
            continue

        raise NotImplementedError("Do not know how to handle field: %s" % field)
    return (
        is_asymmetric,
        is_cursive,
        is_unusual,
        bopomofo,
        is_fully_reflective,
        fully_reflective,
        is_mirrored,
        mirrored,
        is_odd,
        odd,
        is_rotated,
        rotated,
        hangul_component,
        incomplete,
        katakana,
        stroke_heavy,
    )


def import_dictionary_like(sql):
    cursor = sql.cursor()

    dictionary_like_data_by_codepoint = {}

    with open("./assets/Unihan_DictionaryLikeData.txt") as f:
        for line in f.readlines():
            match = READING_RE.match(line)
            if match is not None:
                codepoint = int(match[1], 16)
                dictionary_like_data = (
                    dictionary_like_data_by_codepoint.get(codepoint) or {}
                )
                field_name = match[2]
                field_value = match[3]
                if field_name == "kStrange":
                    (
                        is_asymmetric,
                        is_cursive,
                        is_unusual,
                        bopomofo,
                        is_fully_reflective,
                        fully_reflective,
                        is_mirrored,
                        mirrored,
                        is_odd,
                        odd,
                        is_rotated,
                        rotated,
                        hangul_component,
                        incomplete,
                        katakana,
                        stroke_heavy,
                    ) = parse_strange(codepoint, field_value)
                    dictionary_like_data["is_asymmetric"] = is_asymmetric
                    dictionary_like_data["is_cursive"] = is_cursive
                    dictionary_like_data["is_unusual"] = is_unusual
                    dictionary_like_data["bopomofo"] = bopomofo
                    dictionary_like_data["is_fully_reflective"] = is_fully_reflective
                    dictionary_like_data["fully_reflective"] = fully_reflective
                    dictionary_like_data["is_mirrored"] = is_mirrored
                    dictionary_like_data["mirrored"] = mirrored
                    dictionary_like_data["is_odd"] = is_odd
                    dictionary_like_data["odd"] = odd
                    dictionary_like_data["is_rotated"] = is_rotated
                    dictionary_like_data["rotated"] = rotated
                    dictionary_like_data["hangul_component"] = hangul_component
                    dictionary_like_data["incomplete"] = incomplete
                    dictionary_like_data["katakana"] = katakana
                    dictionary_like_data["stroke_heavy"] = stroke_heavy
                dictionary_like_data[
                    DICTIONARY_LIKE_FIELDS_BY_FIELD_NAME[field_name]
                ] = DICTIONARY_LIKE_CONVERSION_BY_FIELD_NAME[field_name](field_value)
                dictionary_like_data_by_codepoint[codepoint] = dictionary_like_data
            else:
                pass

    dictionary_like_data = [
        (
            codepoint,
            values.get("alternate_total_strokes"),
            values.get("cangjie"),
            values.get("cheung_bauer"),
            values.get("fenn"),
            values.get("four_corner_code"),
            values.get("frequency"),
            values.get("grade_level"),
            values.get("hdz_rad_break"),
            values.get("hk_glyph"),
            values.get("phonetic"),
            values.get("strange"),
            values.get("unihan_core_2020"),
            values.get("is_asymmetric") or False,
            values.get("is_cursive") or False,
            values.get("is_unusual") or False,
            values.get("bopomofo"),
            values.get("is_fully_reflective") or False,
            values.get("fully_reflective"),
            values.get("is_mirrored") or False,
            values.get("mirrored"),
            values.get("is_odd") or False,
            values.get("odd"),
            values.get("is_rotated") or False,
            values.get("rotated"),
            values.get("hangul_component"),
            values.get("incomplete"),
            values.get("katakana"),
            values.get("stroke_heavy"),
        )
        for (codepoint, values) in dictionary_like_data_by_codepoint.items()
    ]
    print(
        "Writing %d dictionary like rows to db"
        % (len(dictionary_like_data_by_codepoint),)
    )
    cursor.executemany(
        "INSERT INTO dictionary_like VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        dictionary_like_data,
    )
    sql.commit()
    print("ok")


def import_cedict(sql):
    cursor = sql.cursor()
    cedict_data_by_morpheme = []

    b = conversion.TonePlacementBuf()
    with open("./assets/cedict_1_0_ts_utf-8_mdbg.txt") as f:
        for line in f.readlines():
            match = CEDICT_RE.match(line)
            if match is not None:
                phonetic_pinyin = b.convert_string(match[3])
                cedict_data_by_morpheme.append(
                    (match[2], match[1], match[3], phonetic_pinyin, match[4])
                )

    print("Writing %d cedict rows to db" % (len(cedict_data_by_morpheme),))
    cursor.executemany(
        "INSERT INTO cedict VALUES (?, ?, ?, ?, ?)",
        cedict_data_by_morpheme,
    )
    sql.commit()
    print("ok")


def import_ids(sql):
    cursor = sql.cursor()
    cedict_data_by_morpheme = []

    with open("./assets/IDS.txt") as f:
        for line in f.readlines():
            parse_ids_line(line)

    print("Writing %d IDS rows to db" % (len(cedict_data_by_morpheme),))
    cursor.executemany(
        "INSERT INTO ids VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        cedict_data_by_morpheme,
    )
    sql.commit()
    print("ok")


# input: the line of the IDS.txt file format to parse
# output: the parsed line, structured to the extent possible.
def parse_ids_line(line):
    # first, split out the codepoint from the rest of the line
    line_match = IDS_RE.match(line)
    if line_match is None:
        return None
    (codepoint, rest) = line_match.groups()
    for source in rest.split("\t"):
        seq_match = IDS_STROKE_SEQUENCE_RE.match(source)
        if seq_match is not None:
            (seq, sources) = seq_match.groups()
            continue

        asterisk_operator_match = IDS_ASTERISK_OPERATOR_RE.match(source)
        if asterisk_operator_match is not None:
            (seq, sources, operator, operand) = asterisk_operator_match.groups()
            continue

        commentary_match = IDS_ASTERIKS_COMMENTARY_RE.match(source)
        if commentary_match is not None:
            (commentary,) = commentary_match.groups()
            continue

        raise RuntimeError(
            "Parse error in IDS.txt; not sure how to parse line: %s" % (line,)
        )


LEVEL_RE = re.compile(r"//HSK (?:3\.0|2012)/Level ([1-9])")


def stream_hsk_file(path):
    word_seen = set()
    with open(path) as f:
        cur_level = None
        for line in f.readlines():
            line = line.strip()
            level_match = LEVEL_RE.match(line)
            if level_match is not None:
                cur_level = int(level_match[1])
            elif line == "":
                next
            elif cur_level is not None:
                if line not in word_seen:
                    yield (line, cur_level)
                    word_seen.add(line)


def stream_hsk():
    hsk_2012_level_by_word = dict(stream_hsk_file("assets/HSK-2012.csv"))
    hsk_2023_level_by_word = dict(stream_hsk_file("assets/hsk30-pleco.txt"))
    keys = set(hsk_2012_level_by_word.keys()).union(set(hsk_2023_level_by_word))
    for key in keys:
        yield (key, hsk_2012_level_by_word.get(key), hsk_2023_level_by_word.get(key))


def import_hsk(sql):
    cursor = sql.cursor()

    hsk_rows = list(stream_hsk())
    print("Writing %d hsk rows to db" % (len(hsk_rows),))
    cursor.executemany("INSERT INTO hsk VALUES (?, ?, ?)", hsk_rows)
    sql.commit()
    print("ok")


def import_variants(sql):
    cursor = sql.cursor()
    semantic_variants = []
    variants = []
    for (
        codepoint,
        variant_type,
        variant_codepoint,
        field,
        field_tag,
    ) in iterate_variants():
        if variant_type in ("kSemanticVariant", "kSpecializedSemanticVariant"):
            is_t = False
            is_b = False
            is_z = False
            is_f = False
            is_j = False
            if field_tag is not None:
                assert field is not None
                is_t = "T" in field_tag
                is_b = "B" in field_tag
                is_z = "Z" in field_tag
                is_f = "F" in field_tag
                is_j = "J" in field_tag
            semantic_variants.append(
                (codepoint, variant_type, field, is_t, is_b, is_z, is_f, is_j)
            )
        variants.append((codepoint, variant_type, variant_codepoint))
    print("Writing %d variant rows to db" % (len(variants),))
    cursor.executemany("INSERT INTO variants VALUES (?, ?, ?);", variants)
    print("ok")
    print("Writing %d semantic variant rows to db" % (len(semantic_variants),))
    cursor.executemany(
        "INSERT INTO semantic_variants VALUES (?, ?, ?, ?, ?, ?, ?, ?);",
        semantic_variants,
    )
    sql.commit()
    print("ok")


def iterate_variants():
    with open("assets/Unihan_Variants.txt") as f:
        for line in f.readlines():
            variant_match = VARIANT_RE.match(line)
            if variant_match is not None:
                (codepoint, variant_type, variant_values) = variant_match.groups()
                codepoint = int(codepoint, 16)
                variants = variant_values.split(" ")
                for variant_value in variants:
                    sourced_match = VARIANT_CODEPOINT_RE.match(variant_value)
                    if sourced_match is None:
                        continue
                    (sourced_codepoint, attributions) = sourced_match.groups()
                    sourced_codepoint = int(sourced_codepoint, 16)
                    if attributions is None:
                        yield (codepoint, variant_type, sourced_codepoint, None, None)
                    else:
                        for attribution in attributions.split(","):
                            field = attribution
                            field_tag = None
                            if ":" in field:
                                (field, field_tag) = attribution.split(":")
                            yield (
                                codepoint,
                                variant_type,
                                sourced_codepoint,
                                field,
                                field_tag,
                            )


if __name__ == "__main__":
    with sqlite3.connect("output/unihan.sqlite3") as sql:
        create_schema(sql)
        import_hsk(sql)
        import_cedict(sql)
        import_dictionary_like(sql)
        import_ids(sql)
        import_readings(sql)
        import_variants(sql)
