use serde::Deserialize;
use wasm_bindgen::prelude::*;
use wasm_bindgen_futures::JsFuture;
use web_sys::{Request, RequestInit, RequestMode, Response};

#[derive(Debug, Deserialize)]
struct PartialCommitResponse {
    sha: String,
}

pub async fn get_text_from_url(url: &str) -> Option<String> {
    let mut opts = RequestInit::new();
    opts.method("GET");
    opts.mode(RequestMode::Cors);

    let request = Request::new_with_str_and_init(url, &opts).ok()?;

    let _ = request.headers().set("Accept", "application/json");

    let window = web_sys::window().unwrap();
    let resp_value = JsFuture::from(window.fetch_with_request(&request))
        .await
        .ok()?;
    assert!(resp_value.is_instance_of::<Response>());

    let resp: Response = resp_value.dyn_into().unwrap();
    let raw_data = &JsFuture::from(resp.text().ok()?).await.ok()?;

    assert!(raw_data.is_string());
    raw_data.as_string()
}

#[wasm_bindgen]
pub async fn get_closest_commit(date: &str) -> Option<String> {
    let api_url = format!(
        "https://api.github.com/repos/neuro-arg/arg-monitoring/commits?sha=publish&until={}&per_page=1",
        date
    );

    let json_value = get_text_from_url(&api_url).await?;
    let commit: Vec<PartialCommitResponse> = serde_json::from_str(&json_value).ok()?;

    if commit.len() == 0 {
        None
    } else {
        Some(commit[0].sha.to_string())
    }
}

#[wasm_bindgen]
pub async fn get_file_from_commit(commit: &str, filename: &str) -> Option<String> {
    let api_url = format!(
        "https://raw.githubusercontent.com/neuro-arg/arg-monitoring/{}/{}",
        commit, filename
    );

    get_text_from_url(&api_url).await
}
