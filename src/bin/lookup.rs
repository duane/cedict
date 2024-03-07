use std::env::args;

fn main() {
    let arg = args().nth(1).expect("Please provide a term");

    let idx = cedict::Index::from_sqlite("unihan/output/unihan.sqlite3");
    println!("{:?}", idx.lookup(&arg));
}
