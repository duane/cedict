mod dictionary_like;

use dictionary_like::DictionaryLike;

use std::collections::HashMap;

pub struct Index {
    dict_like: HashMap<u32, DictionaryLike>,
    by_pinyin: HashMap<String, Vec<DictionaryLike>>,
    by_unaccented_pinyin: HashMap<String, Vec<DictionaryLike>>,
}

impl Index {
    pub fn new() -> Index {
        Index {
            dict_like: HashMap::new(),
            by_pinyin: HashMap::new(),
            by_unaccented_pinyin: HashMap::new(),
        }
    }

    pub fn lookup(&self, query: &str) -> Vec<&DictionaryLike> {
        let mut results = Vec::new();
        for c in query.chars() {
            if let Some(dict_like) = self.dict_like.get(&(c as u32)) {
                results.push(dict_like);
            }
        }
        if let Some(dict_likes) = self.by_pinyin.get(query) {
            results.extend(dict_likes);
        }
        results
    }

    fn ingest_codepoints(&mut self, connection: &rusqlite::Connection) {
        for codepoint in connection
            .prepare("SELECT codepoint from dictionary_like")
            .unwrap()
            .query_map([], |row| Ok(row.get(0)?))
            .unwrap()
        {
            let dict_like = DictionaryLike {
                codepoint: codepoint.unwrap(),
            };
            self.dict_like.insert(dict_like.codepoint, dict_like);
        }
    }

    fn ingest_pinyin(&mut self, connection: &rusqlite::Connection) {
        for res in connection
            .prepare("SELECT codepoint, mandarin from readings where mandarin is not null;")
            .unwrap()
            .query_map([], |row| Ok((row.get(0)?, row.get(1)?)))
            .unwrap()
        {
            let (codepoint, pinyin) = res.unwrap();
            self.by_pinyin
                .entry(pinyin)
                .or_insert(Vec::new())
                .push(DictionaryLike { codepoint });
        }
    }

    pub fn from_sqlite(file: &str) -> Index {
        let connection = rusqlite::Connection::open(file).unwrap();
        let mut idx = Index::new();
        idx.ingest_codepoints(&connection);
        idx.ingest_pinyin(&connection);
        idx
    }
}

/*
    return "\u0304"
if digit == "2":
    return "\u0301"
if digit == "3":
    return "\u0306"
if digit == "4":
    return "\u0300" */
fn strip_diacritics(s: &str) -> String {}
