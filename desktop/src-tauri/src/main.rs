#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use serde_json::{json, Value};
use std::{io::{BufRead, BufReader, Write}, path::PathBuf, process::{Command, Stdio}, sync::{Arc, atomic::{AtomicBool, Ordering}}};
use tauri::{Emitter, Manager};
use tauri_plugin_opener::OpenerExt;

#[derive(Clone, Default)]
struct EngineState { busy: Arc<AtomicBool> }
struct BusyGuard(Arc<AtomicBool>);
impl Drop for BusyGuard { fn drop(&mut self) { self.0.store(false, Ordering::SeqCst); } }

fn command() -> Result<Command, String> {
    let mut cmd = if cfg!(debug_assertions) {
        let worker = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../engine/worker.py");
        let mut c = Command::new(std::env::var("ONI_PYTHON").unwrap_or_else(|_| "python".into()));
        c.args(["-X", "utf8"]).arg(worker); c
    } else {
        let exe = std::env::current_exe().map_err(|e| e.to_string())?;
        Command::new(exe.parent().ok_or("앱 경로를 찾을 수 없습니다.")?.join("oni-engine.exe"))
    };
    #[cfg(windows)] {
        use std::os::windows::process::CommandExt;
        cmd.creation_flags(0x08000000);
    }
    cmd.stdin(Stdio::piped()).stdout(Stdio::piped()).stderr(Stdio::piped());
    Ok(cmd)
}

fn run_worker(app: tauri::AppHandle, mut request: Value) -> Result<Value, String> {
    let dir = app.path().app_data_dir().map_err(|e| e.to_string())?;
    std::fs::create_dir_all(&dir).map_err(|e| e.to_string())?;
    request["dataDir"] = json!(dir);
    let mut child = command()?.spawn().map_err(|e| format!("변환 엔진을 실행하지 못했습니다: {e}"))?;
    let mut stdin = child.stdin.take().ok_or("엔진 입력을 열 수 없습니다.")?;
    if let Err(e) = writeln!(stdin, "{}", request) { let _ = child.kill(); let _ = child.wait(); return Err(e.to_string()); }
    drop(stdin);
    let stderr = child.stderr.take().ok_or("엔진 로그를 열 수 없습니다.")?;
    let err_reader = std::thread::spawn(move || {
        use std::io::Read;
        let mut s = String::new(); let _ = BufReader::new(stderr).read_to_string(&mut s); s
    });
    let stdout = child.stdout.take().ok_or("엔진 출력을 열 수 없습니다.")?;
    let mut result = None;
    for line in BufReader::new(stdout).lines() {
        if let Ok(line) = line {
            if let Ok(v) = serde_json::from_str::<Value>(&line) {
                match v["type"].as_str() {
                    Some("progress") => { let _ = app.emit("engine-progress", &v); },
                    Some("result") => result = Some(Ok(v["data"].clone())),
                    Some("error") => result = Some(Err(v["message"].as_str().unwrap_or("변환 오류").to_string())),
                    _ => {}
                }
            }
        }
    }
    let status = child.wait().map_err(|e| e.to_string())?;
    let details = err_reader.join().unwrap_or_default();
    result.unwrap_or_else(|| Err(format!("변환 엔진이 종료되었습니다 ({status}). {}", details.chars().take(1200).collect::<String>())))
}

#[tauri::command]
async fn engine(app: tauri::AppHandle, state: tauri::State<'_, EngineState>, request: Value) -> Result<Value, String> {
    let action = request["action"].as_str().ok_or("작업이 지정되지 않았습니다.")?;
    if !["inspect", "preview", "convert", "history", "environment", "save_settings", "settings"].contains(&action) { return Err("지원하지 않는 작업입니다.".into()); }
    let guard = if action == "convert" {
        if state.busy.compare_exchange(false, true, Ordering::SeqCst, Ordering::SeqCst).is_err() { return Err("진행 중인 변환이 있습니다.".into()); }
        Some(BusyGuard(state.busy.clone()))
    } else { None };
    tauri::async_runtime::spawn_blocking(move || { let _guard = guard; run_worker(app, request) }).await.map_err(|e| e.to_string())?
}

#[tauri::command]
fn open_local(app: tauri::AppHandle, path: String) -> Result<(), String> {
    let p = std::fs::canonicalize(path).map_err(|_| "파일이나 폴더를 찾을 수 없습니다.".to_string())?;
    if !p.is_dir() && !p.extension().and_then(|x| x.to_str()).is_some_and(|x| ["pdf", "hwpx"].contains(&x.to_lowercase().as_str())) { return Err("PDF와 HWPX 파일만 열 수 있습니다.".into()); }
    app.opener().open_path(p.to_string_lossy().to_string(), None::<&str>).map_err(|e| e.to_string())
}

fn main() {
    tauri::Builder::default()
        .manage(EngineState::default())
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_opener::init())
        .invoke_handler(tauri::generate_handler![engine, open_local])
        .on_window_event(|window, event| {
            if let tauri::WindowEvent::CloseRequested { api, .. } = event {
                if window.state::<EngineState>().busy.load(Ordering::SeqCst) {
                    api.prevent_close(); let _ = window.emit("close-blocked", "변환이 끝나면 창을 닫을 수 있습니다.");
                }
            }
        })
        .run(tauri::generate_context!()).expect("Oni Exam 실행 실패");
}
