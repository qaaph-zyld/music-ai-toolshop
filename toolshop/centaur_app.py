"""Centaur Co-Write Interface (B10).

A Streamlit application providing an interactive human-AI co-writing
interface with real-time quality scoring, cliché highlights, rhyme scheme
visualization, few-shot examples, slang injection, and theme comparison.

Requires ``streamlit`` and ``plotly`` (not installed by default).
All internal module imports use try/except fallback since they are built
in parallel.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Optional

from toolshop.lyricsdb import DEFAULT_DB_PATH


# ── Internal module imports (parallel build — try/except fallback) ─────

def _get_scorer():
    try:
        from toolshop.ai_scorer import score_lyrics
        return score_lyrics
    except ImportError:
        return None


def _get_cliche_checker():
    try:
        from toolshop.cliche_checker import check_cliches
        return check_cliches
    except ImportError:
        return None


def _get_scheme_checker():
    try:
        from toolshop.scheme_checker import check_scheme
        return check_scheme
    except ImportError:
        return None


def _get_similarity_retriever():
    try:
        from toolshop.similarity_retriever import retrieve_similar
        return retrieve_similar
    except ImportError:
        return None


def _get_slang_injector():
    try:
        from toolshop.slang_injector import inject_slang
        return inject_slang
    except ImportError:
        return None


def _get_theme_comparator():
    try:
        from toolshop.theme_comparator import compare_themes
        return compare_themes
    except ImportError:
        return None


# ── Streamlit app code ─────────────────────────────────────────────────

def _run_streamlit_app() -> None:
    """Build and run the Streamlit centaur co-write app.

    This function is only called inside a Streamlit subprocess — all
    ``streamlit`` and ``plotly`` imports are deferred to here.
    """
    import streamlit as st

    st.set_page_config(
        page_title="Centaur Co-Write",
        page_icon="🎵",
        layout="wide",
    )

    st.title("🎵 Centaur Co-Write Interface")
    st.markdown("Human-AI collaborative lyrics writing with real-time feedback.")

    # ── Sidebar: settings ────────────────────────────────────────────
    st.sidebar.header("Settings")
    cohort = st.sidebar.selectbox(
        "Cohort", ["drill_trap", "pop"], index=0
    )
    db_path = st.sidebar.text_input(
        "Database path", str(DEFAULT_DB_PATH)
    )

    # ── Left panel: lyrics editor ────────────────────────────────────
    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("Lyrics Editor")
        lyrics_text = st.text_area(
            "Write or paste lyrics here:",
            height=400,
            placeholder="[Verse 1]\nEnter your lyrics...\n\n[Chorus]\n...",
        )

        # Write to temp file for scoring
        if lyrics_text.strip():
            tmp_path = Path("/tmp/centaur_current.txt")
            if sys.platform == "win32":
                tmp_path = Path("centaur_current.txt")
            tmp_path.write_text(lyrics_text, encoding="utf-8")

    with col_right:
        st.subheader("Quality Dashboard")

        if lyrics_text.strip():
            # ── AI Scorer ─────────────────────────────────────────────
            score_lyrics = _get_scorer()
            if score_lyrics is not None:
                try:
                    result = score_lyrics(
                        input_path=tmp_path,
                        cohort=cohort,
                        db_path=Path(db_path) if db_path else None,
                    )
                    overall = result.get("overall_score", 0)
                    st.metric("Overall Score", f"{overall}/100")

                    components = result.get("components", {})

                    # ── Radar chart via plotly ─────────────────────────
                    try:
                        import plotly.graph_objects as go

                        comp_names = ["Structural", "Rhyme", "Lexical", "Repetition"]
                        comp_keys = ["structural", "rhyme", "lexical", "repetition"]
                        comp_values = []
                        for key in comp_keys:
                            comp = components.get(key, {})
                            val = comp.get("score", 0) if isinstance(comp, dict) else 0
                            comp_values.append(val)

                        fig = go.Figure(data=go.Scatterpolar(
                            r=comp_values + [comp_values[0]],
                            theta=comp_names + [comp_names[0]],
                            fill="toself",
                            name="Quality",
                        ))
                        fig.update_layout(
                            polar=dict(
                                radialaxis=dict(visible=True, range=[0, 100]),
                            ),
                            showlegend=False,
                            height=300,
                        )
                        st.plotly_chart(fig, use_container_width=True)
                    except ImportError:
                        st.info("Install plotly for radar chart visualization.")

                    # ── Component breakdown ────────────────────────────
                    with st.expander("Component Breakdown", expanded=False):
                        for key in ("structural", "rhyme", "lexical", "repetition"):
                            comp = components.get(key, {})
                            if isinstance(comp, dict):
                                st.write(f"**{key.title()}**: {comp.get('score', 0)}")
                except Exception as e:
                    st.error(f"Scoring error: {e}")
            else:
                st.info("ai_scorer module not available.")

            # ── Cliché highlights ─────────────────────────────────────
            check_cliches = _get_cliche_checker()
            if check_cliches is not None:
                try:
                    cliche_result = check_cliches(text=lyrics_text)
                    total = cliche_result.get("total_cliches", 0)
                    density = cliche_result.get("density_pct", 0.0)
                    if total > 0:
                        st.warning(
                            f"⚠️ {total} clichés detected "
                            f"({density:.1f}% density)"
                        )
                        with st.expander("Cliché Details"):
                            for hit in cliche_result.get("per_line_hits", []):
                                st.write(hit)
                    else:
                        st.success("✅ No clichés detected.")
                except Exception as e:
                    st.error(f"Cliché check error: {e}")

            # ── Rhyme scheme visualization ────────────────────────────
            check_scheme = _get_scheme_checker()
            if check_scheme is not None:
                try:
                    scheme_result = check_scheme(
                        input_path=tmp_path,
                        db_path=Path(db_path) if db_path else None,
                    )
                    with st.expander("Rhyme Scheme", expanded=False):
                        for sec in scheme_result.get("sections", []):
                            st.write(
                                f"**{sec.get('type', '?')}**: "
                                f"scheme {sec.get('detected_scheme', 'N/A')}"
                            )
                            broken = sec.get("broken_lines", [])
                            if broken:
                                st.write(f"  Broken lines: {len(broken)}")
                except Exception as e:
                    st.error(f"Rhyme scheme error: {e}")
        else:
            st.info("Start writing lyrics to see quality feedback.")

    # ── Bottom panel: tools ──────────────────────────────────────────
    st.divider()
    st.subheader("Tools")

    tool_col1, tool_col2, tool_col3 = st.columns(3)

    with tool_col1:
        st.markdown("#### Few-Shot Examples")
        retrieve_similar = _get_similarity_retriever()
        if retrieve_similar is not None and lyrics_text.strip():
            if st.button("Find Similar"):
                try:
                    sim_result = retrieve_similar(
                        input_path=tmp_path,
                        cohort=cohort,
                        top_k=5,
                        db_path=Path(db_path) if db_path else None,
                    )
                    for r in sim_result.get("results", []):
                        st.write(
                            f"{r.get('rank', '?')}. "
                            f"**{r.get('artist', '?')}** — "
                            f"{r.get('title', '?')} "
                            f"(sim: {r.get('similarity', 0):.2f})"
                        )
                        with st.expander("Few-shot block"):
                            st.code(r.get("few_shot_block", ""))
                except Exception as e:
                    st.error(f"Similarity search error: {e}")
        elif retrieve_similar is None:
            st.info("similarity_retriever not available.")

    with tool_col2:
        st.markdown("#### Slang Injection")
        inject_slang = _get_slang_injector()
        if inject_slang is not None and lyrics_text.strip():
            density = st.slider("Slang density", 0.01, 0.20, 0.05, 0.01)
            if st.button("Inject Slang"):
                try:
                    slang_result = inject_slang(
                        input_path=tmp_path,
                        cohort=cohort,
                        density=density,
                        db_path=Path(db_path) if db_path else None,
                    )
                    modified = slang_result.get("modified_text", "")
                    injections = slang_result.get("injections", [])
                    st.write(f"Injected {len(injections)} slang terms.")
                    st.text_area("Modified lyrics", modified, height=200)
                except Exception as e:
                    st.error(f"Slang injection error: {e}")
        elif inject_slang is None:
            st.info("slang_injector not available.")

    with tool_col3:
        st.markdown("#### Theme Comparison")
        compare_themes = _get_theme_comparator()
        if compare_themes is not None and lyrics_text.strip():
            if st.button("Compare Themes"):
                try:
                    theme_result = compare_themes(
                        input_path=tmp_path,
                        cohort=cohort,
                        db_path=Path(db_path) if db_path else None,
                    )
                    if "error" in theme_result:
                        st.error(theme_result["error"])
                    else:
                        st.metric(
                            "JSD Score",
                            f"{theme_result.get('jsd_score', 0):.4f}",
                        )
                        st.write("**Over-represented:**")
                        for t in theme_result.get("over_represented", [])[:3]:
                            st.write(
                                f"  Topic {t['topic_id']}: "
                                f"{t['input_pct']:.1%} vs "
                                f"{t['cohort_pct']:.1%}"
                            )
                        st.write("**Under-represented:**")
                        for t in theme_result.get("under_represented", [])[:3]:
                            st.write(
                                f"  Topic {t['topic_id']}: "
                                f"{t['input_pct']:.1%} vs "
                                f"{t['cohort_pct']:.1%}"
                            )
                except Exception as e:
                    st.error(f"Theme comparison error: {e}")
        elif compare_themes is None:
            st.info("theme_comparator not available.")

    # ── Export ───────────────────────────────────────────────────────
    st.divider()
    if st.button("Export Lyrics + Report") and lyrics_text.strip():
        export = {
            "lyrics": lyrics_text,
            "cohort": cohort,
            "quality_report": result if "result" in dir() else None,
        }
        export_json = json.dumps(export, indent=2, ensure_ascii=False)
        st.download_button(
            label="Download JSON",
            data=export_json,
            file_name="centaur_export.json",
            mime="application/json",
        )


# ── Launch function ────────────────────────────────────────────────────

def launch_centaur(port: int = 8501) -> None:
    """Launch the Centaur co-write Streamlit app.

    Args:
        port: Port to run the Streamlit server on (default: 8501).
    """
    try:
        import streamlit  # noqa: F401
    except ImportError:
        print(
            "streamlit is not installed. "
            "Install with: pip install streamlit plotly"
        )
        return

    app_file = Path(__file__).resolve()
    print(f"Launching Centaur Co-Write on port {port}...")
    subprocess.run(
        [
            sys.executable, "-m", "streamlit", "run",
            str(app_file),
            "--server.port", str(port),
            "--",
        ],
        check=False,
    )


# ── Streamlit entry point ──────────────────────────────────────────────

if __name__ == "__main__":
    _run_streamlit_app()
