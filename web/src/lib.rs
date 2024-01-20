mod fetcher;
mod states;
mod utils;

use fetcher::*;
use serde::Serialize;
use serde_json::from_str;
use states::{get_match_tuples, ArgState};
use std::collections::HashMap;
use utils::*;
use wasm_bindgen::prelude::*;
extern crate web_sys;

#[wasm_bindgen]
extern "C" {
    fn alert(s: &str);
}

#[derive(Serialize)]
struct NeatlyPackedRetVal<'a> {
    lhs_state: &'a ArgState,
    rhs_state: &'a ArgState,
    match_tuples: HashMap<String, bool>,
    lhs_commit: &'a str,
    rhs_commit: &'a str,
}

pub async fn get_cache_on_date(date: &str) -> (String, String) {
    let closest_commit = get_closest_commit(date)
        .await
        .unwrap_or_else(|| {
            error!("Error occured while getting nearest commit to date. Defaulting to no available cache (nulls)");
            return "".to_string();
        })
        .to_string();

    if closest_commit == "" {
        return ("{}".to_string(), "".to_string());
    }

    (
        get_file_from_commit(&closest_commit, "cache.json")
            .await
            .unwrap_or_else(|| {
                error!("Error occured while getting cache from nearest commit. Using empty list");
                "{}".to_string()
            }).to_string(),
        closest_commit.to_string(),
    )
}

#[wasm_bindgen]
pub async fn compare_cache_on_dates(
    date_lhs: &str,
    date_rhs: &str,
) -> Result<JsValue, serde_wasm_bindgen::Error> {
    let (state_lhs, lhs_commit): (ArgState, String) = {
        let (cache, commit) = get_cache_on_date(date_lhs).await;
        (from_str(cache.as_str()).unwrap_or_else(|err| {
            error!(
                "Error occured while converting result to {}: {}. Original JSON: {}",
                date_rhs, err, cache
            );
            panic!();
        }), commit)
    };

    let (state_rhs, rhs_commit): (ArgState, String) = {
        let (cache, commit) = get_cache_on_date(date_rhs).await;
        (from_str(cache.as_str()).unwrap_or_else(|err| {
            error!(
                "Error occured while converting result to {}: {}. Original JSON: {}",
                date_rhs, err, cache
            );
            panic!();
        }), commit)
    };

    serde_wasm_bindgen::to_value(&NeatlyPackedRetVal {
        lhs_state: &state_lhs,
        rhs_state: &state_rhs,
        match_tuples: get_match_tuples(&state_lhs, &state_rhs),
        lhs_commit: &lhs_commit,
        rhs_commit: &rhs_commit,
    })
}
