use std::env;
use std::path::PathBuf;
use std::process::Command;

fn main() {
    println!("cargo:rerun-if-changed=../../AGENTS.md");
    println!("cargo:rerun-if-changed=build_support/render_agents_prompt.py");

    let manifest_dir = PathBuf::from(env::var("CARGO_MANIFEST_DIR").expect("CARGO_MANIFEST_DIR"));
    let repo_root = manifest_dir
        .parent()
        .and_then(|path| path.parent())
        .expect("codex-rs/core should be two levels below the repository root");
    let out_dir = PathBuf::from(env::var("OUT_DIR").expect("OUT_DIR"));
    let script = manifest_dir.join("build_support/render_agents_prompt.py");
    let input = repo_root.join("AGENTS.md");
    let output_png = out_dir.join("codex_repo_agents_prompt.png");
    let output_rs = out_dir.join("codex_repo_agents_prompt.rs");

    let python = env::var("PYTHON").unwrap_or_else(|_| "python3".to_string());
    let status = Command::new(&python)
        .arg(script)
        .arg("--input")
        .arg(input)
        .arg("--output-png")
        .arg(output_png)
        .arg("--output-rs")
        .arg(output_rs)
        .status()
        .unwrap_or_else(|error| panic!("failed to run {python}: {error}"));

    assert!(
        status.success(),
        "AGENTS.md image generation failed; install Python Pillow (PIL) for the build environment"
    );
}
