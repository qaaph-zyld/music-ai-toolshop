"""CLI handler for the `toolshop daw` command.

Subcommands:
    status          - Show DAW connection state and project info
    transport       - Play/stop/tempo/metronome/record controls
    mixer           - Mixer state and controls
    channels        - Channel rack listing and step sequencer
    patterns        - Pattern management
    playlist        - Playlist track info
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Optional, Sequence

from .client import (
    DAWClient,
    DAWConnectionError,
    DAWServerError,
    DAWTimeoutError,
    DEFAULT_HOST,
    DEFAULT_PORT,
)
from . import transport


def add_parser(subparsers: argparse._SubParsersAction) -> None:
    """Register the `daw` subcommand on the given subparsers."""
    daw_parser = subparsers.add_parser(
        "daw",
        help="Live DAW control via TCP bridge (FL Studio, Ableton, openDAW)",
    )
    daw_parser.add_argument(
        "--host",
        type=str,
        default=DEFAULT_HOST,
        help=f"TCP host (default: {DEFAULT_HOST})",
    )
    daw_parser.add_argument(
        "--port",
        type=int,
        default=DEFAULT_PORT,
        help=f"TCP port (default: {DEFAULT_PORT})",
    )
    daw_parser.add_argument(
        "--timeout",
        type=float,
        default=5.0,
        help="Command timeout in seconds (default: 5.0)",
    )

    daw_subparsers = daw_parser.add_subparsers(dest="daw_command")
    daw_subparsers.required = True

    # status
    daw_subparsers.add_parser(
        "status", help="Show DAW connection state and project info"
    )

    # transport
    transport_parser = daw_subparsers.add_parser(
        "transport", help="Transport controls (play/stop/tempo/etc.)"
    )
    transport_subparsers = transport_parser.add_subparsers(dest="transport_command")
    transport_subparsers.required = True

    transport_subparsers.add_parser("play", help="Start playback")
    transport_subparsers.add_parser("stop", help="Stop playback")
    transport_subparsers.add_parser("state", help="Get full transport state")

    tempo_get = transport_subparsers.add_parser("get-tempo", help="Get current BPM")
    tempo_get.add_argument("--json", action="store_true", help="Output as JSON")

    tempo_set = transport_subparsers.add_parser("set-tempo", help="Set BPM")
    tempo_set.add_argument("bpm", type=float, help="Tempo in BPM")
    tempo_set.add_argument("--json", action="store_true", help="Output as JSON")

    metro_parser = transport_subparsers.add_parser(
        "metronome", help="Toggle or set metronome"
    )
    metro_parser.add_argument(
        "--on", action="store_true", help="Enable metronome"
    )
    metro_parser.add_argument(
        "--off", action="store_true", help="Disable metronome"
    )
    metro_parser.add_argument("--json", action="store_true", help="Output as JSON")

    transport_subparsers.add_parser("record", help="Start recording")

    timesig_parser = transport_subparsers.add_parser(
        "time-sig", help="Get or set time signature"
    )
    timesig_parser.add_argument(
        "--set", action="store_true", help="Set time signature (default: get)"
    )
    timesig_parser.add_argument("--numerator", type=int, default=None, help="Numerator")
    timesig_parser.add_argument(
        "--denominator", type=int, default=None, help="Denominator"
    )
    timesig_parser.add_argument("--json", action="store_true", help="Output as JSON")

    pos_parser = transport_subparsers.add_parser(
        "position", help="Get playback position"
    )
    pos_parser.add_argument("--json", action="store_true", help="Output as JSON")

    # mixer
    mixer_parser = daw_subparsers.add_parser("mixer", help="Mixer controls")
    mixer_subparsers = mixer_parser.add_subparsers(dest="mixer_command")
    mixer_subparsers.required = True

    mixer_state = mixer_subparsers.add_parser("state", help="Get full mixer state")
    mixer_state.add_argument("--json", action="store_true", help="Output as JSON")

    mixer_vol = mixer_subparsers.add_parser("set-volume", help="Set track volume")
    mixer_vol.add_argument("track", type=int, help="Mixer track index")
    mixer_vol.add_argument("level", type=float, help="Volume level (0.0-1.0)")
    mixer_vol.add_argument("--json", action="store_true", help="Output as JSON")

    mixer_pan = mixer_subparsers.add_parser("set-pan", help="Set track pan")
    mixer_pan.add_argument("track", type=int, help="Mixer track index")
    mixer_pan.add_argument("pan", type=float, help="Pan (-1.0 to 1.0)")
    mixer_pan.add_argument("--json", action="store_true", help="Output as JSON")

    mixer_mute = mixer_subparsers.add_parser("mute", help="Mute a track")
    mixer_mute.add_argument("track", type=int, help="Mixer track index")
    mixer_mute.add_argument("--json", action="store_true", help="Output as JSON")

    mixer_solo = mixer_subparsers.add_parser("solo", help="Solo a track")
    mixer_solo.add_argument("track", type=int, help="Mixer track index")
    mixer_solo.add_argument("--json", action="store_true", help="Output as JSON")

    mixer_route = mixer_subparsers.add_parser("route", help="Route a track to another")
    mixer_route.add_argument("track", type=int, help="Source mixer track index")
    mixer_route.add_argument("to", type=int, help="Destination mixer track index")
    mixer_route.add_argument("--json", action="store_true", help="Output as JSON")

    mixer_addfx = mixer_subparsers.add_parser("add-fx", help="Add FX plugin to track")
    mixer_addfx.add_argument("track", type=int, help="Mixer track index")
    mixer_addfx.add_argument("plugin", type=str, help="Plugin name")
    mixer_addfx.add_argument("--json", action="store_true", help="Output as JSON")

    mixer_fxparams = mixer_subparsers.add_parser("fx-params", help="Get FX params for a track")
    mixer_fxparams.add_argument("track", type=int, help="Mixer track index")
    mixer_fxparams.add_argument("--slot", type=int, default=0, help="Plugin slot index")
    mixer_fxparams.add_argument("--json", action="store_true", help="Output as JSON")

    mixer_setfxparam = mixer_subparsers.add_parser("set-fx-param", help="Set FX parameter")
    mixer_setfxparam.add_argument("track", type=int, help="Mixer track index")
    mixer_setfxparam.add_argument("--slot", type=int, default=0, help="Plugin slot index")
    mixer_setfxparam.add_argument("param", type=int, help="Parameter index")
    mixer_setfxparam.add_argument("value", type=float, help="Parameter value (0.0-1.0)")
    mixer_setfxparam.add_argument("--json", action="store_true", help="Output as JSON")

    # channels
    channels_parser = daw_subparsers.add_parser(
        "channels", help="Channel rack controls"
    )
    channels_subparsers = channels_parser.add_subparsers(dest="channels_command")
    channels_subparsers.required = True

    channels_list = channels_subparsers.add_parser("list", help="List all channels")
    channels_list.add_argument("--json", action="store_true", help="Output as JSON")

    channels_step = channels_subparsers.add_parser(
        "step", help="Get or set a step sequencer cell"
    )
    channels_step.add_argument("channel", type=int, help="Channel index")
    channels_step.add_argument("step", type=int, help="Step index (0-15 for 16-step)")
    channels_step.add_argument(
        "--set", action="store_true", help="Set the step (default: get)"
    )
    channels_step.add_argument(
        "--active", action="store_true", help="Activate the step (with --set)"
    )
    channels_step.add_argument("--json", action="store_true", help="Output as JSON")

    channels_add = channels_subparsers.add_parser("add", help="Add a new channel")
    channels_add.add_argument("--name", type=str, default="", help="Channel name")
    channels_add.add_argument(
        "--type", type=str, default="sampler", help="Channel type (sampler/synth)"
    )
    channels_add.add_argument("--json", action="store_true", help="Output as JSON")

    channels_rename = channels_subparsers.add_parser("rename", help="Rename a channel")
    channels_rename.add_argument("index", type=int, help="Channel index")
    channels_rename.add_argument("name", type=str, help="New name")
    channels_rename.add_argument("--json", action="store_true", help="Output as JSON")

    channels_color = channels_subparsers.add_parser("set-color", help="Set channel color")
    channels_color.add_argument("index", type=int, help="Channel index")
    channels_color.add_argument("color", type=str, help="Color hex (e.g. 0xFF0000 or #FF0000)")
    channels_color.add_argument("--json", action="store_true", help="Output as JSON")

    channels_steppat = channels_subparsers.add_parser(
        "step-pattern", help="Get full step pattern for a channel"
    )
    channels_steppat.add_argument("channel", type=int, help="Channel index")
    channels_steppat.add_argument(
        "--length", type=int, default=16, help="Number of steps (default: 16)"
    )
    channels_steppat.add_argument("--json", action="store_true", help="Output as JSON")

    # patterns
    patterns_parser = daw_subparsers.add_parser("patterns", help="Pattern management")
    patterns_subparsers = patterns_parser.add_subparsers(dest="patterns_command")
    patterns_subparsers.required = True

    patterns_list = patterns_subparsers.add_parser("list", help="List all patterns")
    patterns_list.add_argument("--json", action="store_true", help="Output as JSON")

    patterns_create = patterns_subparsers.add_parser("create", help="Create a pattern")
    patterns_create.add_argument("--name", type=str, default="", help="Pattern name")
    patterns_create.add_argument("--json", action="store_true", help="Output as JSON")

    patterns_rename = patterns_subparsers.add_parser("rename", help="Rename a pattern")
    patterns_rename.add_argument("index", type=int, help="Pattern index")
    patterns_rename.add_argument("name", type=str, help="New name")
    patterns_rename.add_argument("--json", action="store_true", help="Output as JSON")

    patterns_clone = patterns_subparsers.add_parser("clone", help="Clone a pattern")
    patterns_clone.add_argument("index", type=int, help="Pattern index to clone")
    patterns_clone.add_argument("--name", type=str, default="", help="Name for the clone")
    patterns_clone.add_argument("--json", action="store_true", help="Output as JSON")

    # playlist
    playlist_parser = daw_subparsers.add_parser("playlist", help="Playlist info")
    playlist_subparsers = playlist_parser.add_subparsers(dest="playlist_command")
    playlist_subparsers.required = True

    playlist_tracks = playlist_subparsers.add_parser(
        "tracks", help="List playlist tracks"
    )
    playlist_tracks.add_argument("--json", action="store_true", help="Output as JSON")

    # piano-roll
    pr_parser = daw_subparsers.add_parser("piano-roll", help="Piano roll note operations")
    pr_subparsers = pr_parser.add_subparsers(dest="piano_roll_command")
    pr_subparsers.required = True

    pr_add = pr_subparsers.add_parser("add-notes", help="Add notes to a pattern")
    pr_add.add_argument("pattern", type=int, help="Pattern index")
    pr_add.add_argument("notes", type=str, help="Comma-separated note names (e.g. C4,E4,G4)")
    pr_add.add_argument("--position", type=int, default=0, help="Step position (default: 0)")
    pr_add.add_argument("--length", type=int, default=16, help="Note length in steps (default: 16)")
    pr_add.add_argument("--velocity", type=int, default=100, help="MIDI velocity 0-127 (default: 100)")
    pr_add.add_argument("--json", action="store_true", help="Output as JSON")

    pr_clear = pr_subparsers.add_parser("clear", help="Clear all notes from a pattern")
    pr_clear.add_argument("pattern", type=int, help="Pattern index")
    pr_clear.add_argument("--json", action="store_true", help="Output as JSON")

    pr_get = pr_subparsers.add_parser("get-notes", help="Get all notes from a pattern")
    pr_get.add_argument("pattern", type=int, help="Pattern index")
    pr_get.add_argument("--json", action="store_true", help="Output as JSON")

    pr_quant = pr_subparsers.add_parser("quantize", help="Quantize notes in a pattern")
    pr_quant.add_argument("pattern", type=int, help="Pattern index")
    pr_quant.add_argument("--grid", type=int, default=16, help="Grid resolution (4/8/16/32, default: 16)")
    pr_quant.add_argument("--json", action="store_true", help="Output as JSON")

    pr_trans = pr_subparsers.add_parser("transpose", help="Transpose notes in a pattern")
    pr_trans.add_argument("pattern", type=int, help="Pattern index")
    pr_trans.add_argument("semitones", type=int, help="Semitones to transpose (positive=up, negative=down)")
    pr_trans.add_argument("--json", action="store_true", help="Output as JSON")

    pr_human = pr_subparsers.add_parser("humanize", help="Humanize note timing and velocity")
    pr_human.add_argument("pattern", type=int, help="Pattern index")
    pr_human.add_argument("--amount", type=float, default=0.3, help="Humanization amount 0.0-1.0 (default: 0.3)")
    pr_human.add_argument("--seed", type=int, default=42, help="Random seed (default: 42)")
    pr_human.add_argument("--json", action="store_true", help="Output as JSON")

    # plugins
    plugins_parser = daw_subparsers.add_parser("plugins", help="Plugin discovery and parameter control")
    plugins_subparsers = plugins_parser.add_subparsers(dest="plugins_command")
    plugins_subparsers.required = True

    plugins_list = plugins_subparsers.add_parser("list", help="List installed plugins on disk")
    plugins_list.add_argument("--json", action="store_true", help="Output as JSON")

    plugins_params = plugins_subparsers.add_parser("params", help="Get all params for a plugin")
    plugins_params.add_argument("track", type=int, help="Mixer track index")
    plugins_params.add_argument("--slot", type=int, default=0, help="Plugin slot index")
    plugins_params.add_argument("--json", action="store_true", help="Output as JSON")

    plugins_setparam = plugins_subparsers.add_parser("set-param", help="Set a plugin parameter")
    plugins_setparam.add_argument("track", type=int, help="Mixer track index")
    plugins_setparam.add_argument("--slot", type=int, default=0, help="Plugin slot index")
    plugins_setparam.add_argument("param", type=int, help="Parameter index")
    plugins_setparam.add_argument("value", type=float, help="Parameter value (0.0-1.0)")
    plugins_setparam.add_argument("--json", action="store_true", help="Output as JSON")

    # gen (generators)
    gen_parser = daw_subparsers.add_parser("gen", help="High-level musical generators")
    gen_subparsers = gen_parser.add_subparsers(dest="gen_command")
    gen_subparsers.required = True

    gen_drums = gen_subparsers.add_parser("drum-pattern", help="Generate drum pattern in step sequencer")
    gen_drums.add_argument("--genre", type=str, default="drill", help="Genre: drill/trap/pop/boom_bap")
    gen_drums.add_argument("--bars", type=int, default=4, help="Number of bars (default: 4)")
    gen_drums.add_argument("--kick", type=int, default=0, help="Kick channel index")
    gen_drums.add_argument("--snare", type=int, default=1, help="Snare channel index")
    gen_drums.add_argument("--hat", type=int, default=2, help="Hat channel index")
    gen_drums.add_argument("--json", action="store_true", help="Output as JSON")

    gen_chords = gen_subparsers.add_parser("chord-progression", help="Generate chord progression in piano roll")
    gen_chords.add_argument("pattern", type=int, help="Pattern index")
    gen_chords.add_argument("--key", type=str, default="Gm", help="Root key (e.g. Gm, C)")
    gen_chords.add_argument("--scale", type=str, default="minor", help="Scale name")
    gen_chords.add_argument("--progression", type=str, default="i-VI-III-VII", help="Progression (e.g. i-VI-III-VII)")
    gen_chords.add_argument("--bars", type=int, default=8, help="Total bars")
    gen_chords.add_argument("--length", type=int, default=16, help="Chord length in steps")
    gen_chords.add_argument("--json", action="store_true", help="Output as JSON")

    gen_bass = gen_subparsers.add_parser("bassline", help="Generate bassline in piano roll")
    gen_bass.add_argument("pattern", type=int, help="Pattern index")
    gen_bass.add_argument("--key", type=str, default="Gm", help="Root key")
    gen_bass.add_argument("--scale", type=str, default="minor", help="Scale name")
    gen_bass.add_argument("--bars", type=int, default=8, help="Total bars")
    gen_bass.add_argument("--style", type=str, default="root", help="Style: root/octaves/walking")
    gen_bass.add_argument("--length", type=int, default=8, help="Note length in steps")
    gen_bass.add_argument("--json", action="store_true", help="Output as JSON")

    gen_mel = gen_subparsers.add_parser("melody", help="Generate melody in piano roll")
    gen_mel.add_argument("pattern", type=int, help="Pattern index")
    gen_mel.add_argument("--key", type=str, default="Gm", help="Root key")
    gen_mel.add_argument("--scale", type=str, default="minor", help="Scale name")
    gen_mel.add_argument("--bars", type=int, default=4, help="Total bars")
    gen_mel.add_argument("--density", type=float, default=0.5, help="Note density 0.0-1.0")
    gen_mel.add_argument("--seed", type=int, default=42, help="Random seed")
    gen_mel.add_argument("--json", action="store_true", help="Output as JSON")

    gen_arp = gen_subparsers.add_parser("arpeggio", help="Generate arpeggio in piano roll")
    gen_arp.add_argument("pattern", type=int, help="Pattern index")
    gen_arp.add_argument("--chords", type=str, default="Gm,Bb,Dm", help="Comma-separated chord roots")
    gen_arp.add_argument("--type", type=str, default="up", help="Pattern: up/down/updown/random")
    gen_arp.add_argument("--bars", type=int, default=4, help="Total bars")
    gen_arp.add_argument("--length", type=int, default=2, help="Note length in steps")
    gen_arp.add_argument("--octave", type=int, default=4, help="Starting octave")
    gen_arp.add_argument("--json", action="store_true", help="Output as JSON")

    # corpus (corpus intelligence)
    corpus_parser = daw_subparsers.add_parser("corpus", help="Corpus intelligence from lyrics DB")
    corpus_subparsers = corpus_parser.add_subparsers(dest="corpus_command")
    corpus_subparsers.required = True

    corpus_bpm = corpus_subparsers.add_parser("suggest-bpm", help="Suggest BPM for a genre")
    corpus_bpm.add_argument("genre", type=str, help="Genre (drill_trap/pop/trap/boom_bap)")
    corpus_bpm.add_argument("--json", action="store_true", help="Output as JSON")

    corpus_key = corpus_subparsers.add_parser("suggest-key", help="Suggest keys for a genre")
    corpus_key.add_argument("genre", type=str, help="Genre")
    corpus_key.add_argument("--json", action="store_true", help="Output as JSON")

    corpus_arr = corpus_subparsers.add_parser("suggest-arrangement", help="Suggest arrangement for a genre")
    corpus_arr.add_argument("genre", type=str, help="Genre")
    corpus_arr.add_argument("--json", action="store_true", help="Output as JSON")

    corpus_pat = corpus_subparsers.add_parser("suggest-pattern", help="Suggest drum pattern for a genre")
    corpus_pat.add_argument("genre", type=str, help="Genre")
    corpus_pat.add_argument("--json", action="store_true", help="Output as JSON")

    corpus_stats = corpus_subparsers.add_parser("section-stats", help="Get section type stats for a genre")
    corpus_stats.add_argument("genre", type=str, help="Genre")
    corpus_stats.add_argument("--json", action="store_true", help="Output as JSON")

    corpus_flow = corpus_subparsers.add_parser("flow-to-midi", help="Map lyrics syllable density to MIDI density")
    corpus_flow.add_argument("lyrics_file", type=str, help="Path to lyrics text file")
    corpus_flow.add_argument("--json", action="store_true", help="Output as JSON")


def run(args: argparse.Namespace) -> int:
    """Execute the `daw` subcommand."""
    client = DAWClient(
        host=getattr(args, "host", DEFAULT_HOST),
        port=getattr(args, "port", DEFAULT_PORT),
        timeout=getattr(args, "timeout", 5.0),
    )

    try:
        client.connect()
    except DAWConnectionError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        print(
            "Make sure FL Studio is running with the ToolshopDAW script enabled.\n"
            "See: toolshop daw --help for setup instructions.",
            file=sys.stderr,
        )
        return 1

    try:
        return _dispatch(client, args)
    except DAWServerError as exc:
        print(f"DAW error: {exc}", file=sys.stderr)
        return 1
    except DAWTimeoutError as exc:
        print(f"Timeout: {exc}", file=sys.stderr)
        return 1
    finally:
        client.disconnect()


def _dispatch(client: DAWClient, args: argparse.Namespace) -> int:
    """Route to the appropriate handler based on args.daw_command."""
    cmd = args.daw_command

    if cmd == "status":
        return _cmd_status(client)
    elif cmd == "transport":
        return _cmd_transport(client, args)
    elif cmd == "mixer":
        return _cmd_mixer(client, args)
    elif cmd == "channels":
        return _cmd_channels(client, args)
    elif cmd == "patterns":
        return _cmd_patterns(client, args)
    elif cmd == "playlist":
        return _cmd_playlist(client, args)
    elif cmd == "piano-roll":
        return _cmd_piano_roll(client, args)
    elif cmd == "plugins":
        return _cmd_plugins(client, args)
    elif cmd == "gen":
        return _cmd_gen(client, args)
    elif cmd == "corpus":
        return _cmd_corpus(client, args)
    else:
        print(f"Unknown daw command: {cmd}", file=sys.stderr)
        return 1


def _cmd_status(client: DAWClient) -> int:
    """Handle `toolshop daw status`."""
    info = client.status()
    print(f"Bridge:    {info.get('bridge', 'unknown')}")
    print(f"Connected: {info.get('connected', False)}")
    if "fl_version" in info:
        print(f"FL Version: {info['fl_version']}")
        print(f"Tempo:     {info.get('tempo', '?')} BPM")
        print(f"Playing:   {info.get('playing', False)}")
        print(f"Metronome: {info.get('metronome', False)}")
    return 0


def _cmd_transport(client: DAWClient, args: argparse.Namespace) -> int:
    """Handle `toolshop daw transport <subcommand>`."""
    sub = args.transport_command

    if sub == "play":
        result = transport.play(client)
        print("Playback started")
        return 0

    elif sub == "stop":
        result = transport.stop(client)
        print("Playback stopped")
        return 0

    elif sub == "state":
        result = transport.get_state(client)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Playing:    {result.get('playing', False)}")
            print(f"Tempo:      {result.get('tempo', '?')} BPM")
            print(f"Metronome:  {result.get('metronome', False)}")
            print(f"Recording:  {result.get('recording', False)}")
            pos = result.get("position", 0)
            print(f"Position:   {pos:.2f}s")
        return 0

    elif sub == "get-tempo":
        result = transport.get_tempo(client)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"BPM: {result.get('tempo', '?')}")
        return 0

    elif sub == "set-tempo":
        result = transport.set_tempo(client, args.bpm)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Tempo set to {result.get('tempo', args.bpm)} BPM")
        return 0

    elif sub == "metronome":
        if args.on:
            result = transport.set_metronome(client, True)
        elif args.off:
            result = transport.set_metronome(client, False)
        else:
            state = transport.get_state(client)
            current = state.get("metronome", False)
            result = transport.set_metronome(client, not current)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            state = "on" if result.get("metronome") else "off"
            print(f"Metronome: {state}")
        return 0

    elif sub == "record":
        transport.record(client)
        print("Recording started")
        return 0

    elif sub == "time-sig":
        if args.set:
            if not args.numerator or not args.denominator:
                print("Error: --set requires --numerator and --denominator", file=sys.stderr)
                return 1
            result = transport.set_time_signature(
                client, args.numerator, args.denominator
            )
        else:
            result = transport.get_time_signature(client)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Time signature: {result.get('numerator', '?')}/{result.get('denominator', '?')}")
        return 0

    elif sub == "position":
        result = transport.get_position(client)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Position:    {result.get('song_pos_seconds', 0):.2f}s")
            print(f"In beats:    {result.get('song_pos_beats', 0):.2f}")
            print(f"Song length: {result.get('song_length_seconds', 0):.2f}s")
        return 0

    else:
        print(f"Unknown transport command: {sub}", file=sys.stderr)
        return 1


def _cmd_mixer(client: DAWClient, args: argparse.Namespace) -> int:
    """Handle `toolshop daw mixer <subcommand>`."""
    sub = args.mixer_command

    if sub == "state":
        result = client.call("mixer.get_state")
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            tracks = result.get("tracks", [])
            print(f"Mixer tracks: {result.get('track_count', 0)}")
            print(f"\n{'Idx':>4} {'Name':<20} {'Vol':>8} {'Pan':>8} {'Mute':>5} {'Solo':>5}")
            print("-" * 55)
            for t in tracks:
                print(
                    f"{t['index']:>4} {t['name']:<20} "
                    f"{t['volume']:>8.2f} {t['pan']:>8.2f} "
                    f"{'Y' if t['muted'] else '':>5} "
                    f"{'Y' if t['soloed'] else '':>5}"
                )
        return 0

    elif sub == "set-volume":
        result = client.call("mixer.set_volume", track=args.track, level=args.level)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Track {args.track} volume set to {args.level}")
        return 0

    elif sub == "set-pan":
        result = client.call("mixer.set_pan", track=args.track, pan=args.pan)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Track {args.track} pan set to {args.pan}")
        return 0

    elif sub == "mute":
        result = client.call("mixer.mute", track=args.track, muted=True)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Track {args.track} muted")
        return 0

    elif sub == "solo":
        result = client.call("mixer.solo", track=args.track, soloed=True)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Track {args.track} soloed")
        return 0

    elif sub == "route":
        result = client.call("mixer.route", track=args.track, to_track=getattr(args, "to"))
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Track {args.track} routed to {getattr(args, 'to')}")
        return 0

    elif sub == "add-fx":
        result = client.call("mixer.add_fx", track=args.track, plugin_name=args.plugin)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Added '{args.plugin}' to track {args.track} (slot {result.get('slot', 0)})")
        return 0

    elif sub == "fx-params":
        result = client.call("mixer.get_fx_params", track=args.track, slot=args.slot)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            params = result.get("params", [])
            print(f"Track {args.track} slot {args.slot}: {result.get('param_count', 0)} params")
            print(f"\n{'Idx':>4} {'Name':<25} {'Value':>8}")
            print("-" * 40)
            for p in params:
                print(f"{p['index']:>4} {p['name']:<25} {p['value']:>8.3f}")
        return 0

    elif sub == "set-fx-param":
        result = client.call(
            "mixer.set_fx_param",
            track=args.track,
            slot=args.slot,
            param_index=args.param,
            value=args.value,
        )
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Track {args.track} slot {args.slot} param {args.param} = {args.value}")
        return 0

    else:
        print(f"Unknown mixer command: {sub}", file=sys.stderr)
        return 1


def _cmd_channels(client: DAWClient, args: argparse.Namespace) -> int:
    """Handle `toolshop daw channels <subcommand>`."""
    sub = args.channels_command

    if sub == "list":
        result = client.call("channels.list")
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            chs = result.get("channels", [])
            print(f"Channels: {result.get('channel_count', 0)}")
            print(f"\n{'Idx':>4} {'Name':<25} {'Vol':>8} {'Pan':>8}")
            print("-" * 50)
            for c in chs:
                print(
                    f"{c['index']:>4} {c['name']:<25} "
                    f"{c.get('volume', 0):>8.2f} {c.get('pan', 0):>8.2f}"
                )
        return 0

    elif sub == "step":
        if args.set:
            result = client.call(
                "channels.set_step",
                channel=args.channel,
                step=args.step,
                active=args.active,
            )
            action = "activated" if args.active else "deactivated"
            if args.json:
                print(json.dumps(result, indent=2))
            else:
                print(f"Channel {args.channel} step {args.step} {action}")
        else:
            result = client.call(
                "channels.get_step", channel=args.channel, step=args.step
            )
            if args.json:
                print(json.dumps(result, indent=2))
            else:
                state = "active" if result.get("active") else "inactive"
                print(f"Channel {args.channel} step {args.step}: {state}")
        return 0

    elif sub == "add":
        result = client.call("channels.add", name=args.name, channel_type=getattr(args, "type", "sampler"))
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Created channel {result.get('index')}: {result.get('name')}")
        return 0

    elif sub == "rename":
        result = client.call("channels.rename", index=args.index, name=args.name)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Renamed channel {args.index} to '{args.name}'")
        return 0

    elif sub == "set-color":
        color_val = int(args.color, 16) if args.color.startswith(("0x", "#")) else int(args.color)
        result = client.call("channels.set_color", index=args.index, color=color_val)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Channel {args.index} color set to {args.color}")
        return 0

    elif sub == "step-pattern":
        result = client.call("channels.get_step_pattern", channel=args.channel, length=args.length)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            steps = result.get("steps", [])
            display = "".join("X" if s else "." for s in steps)
            print(f"Channel {args.channel} ({len(steps)} steps):")
            print(display)
        return 0

    else:
        print(f"Unknown channels command: {sub}", file=sys.stderr)
        return 1


def _cmd_patterns(client: DAWClient, args: argparse.Namespace) -> int:
    """Handle `toolshop daw patterns <subcommand>`."""
    sub = args.patterns_command

    if sub == "list":
        result = client.call("patterns.list")
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            pats = result.get("patterns", [])
            print(f"Patterns: {result.get('pattern_count', 0)}")
            print(f"\n{'Idx':>4} {'Name':<25} {'Length':>8}")
            print("-" * 40)
            for p in pats:
                print(f"{p['index']:>4} {p['name']:<25} {p.get('length', 0):>8}")
        return 0

    elif sub == "create":
        result = client.call("patterns.create", name=args.name)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Created pattern {result.get('index')}: {result.get('name')}")
        return 0

    elif sub == "rename":
        result = client.call("patterns.rename", index=args.index, name=args.name)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Renamed pattern {args.index} to '{args.name}'")
        return 0

    elif sub == "clone":
        result = client.call("patterns.clone", index=args.index, name=args.name)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Cloned pattern {args.index} → {result.get('index')}: {result.get('name')}")
        return 0

    else:
        print(f"Unknown patterns command: {sub}", file=sys.stderr)
        return 1


def _cmd_playlist(client: DAWClient, args: argparse.Namespace) -> int:
    """Handle `toolshop daw playlist <subcommand>`."""
    sub = args.playlist_command

    if sub == "tracks":
        result = client.call("playlist.get_track_names")
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            tracks = result.get("tracks", [])
            print(f"Playlist tracks: {result.get('track_count', 0)}")
            print(f"\n{'Idx':>4} {'Name':<30}")
            print("-" * 36)
            for t in tracks:
                print(f"{t['index']:>4} {t['name']:<30}")
        return 0

    else:
        print(f"Unknown playlist command: {sub}", file=sys.stderr)
        return 1


def _cmd_piano_roll(client: DAWClient, args: argparse.Namespace) -> int:
    """Handle `toolshop daw piano-roll <subcommand>`."""
    from . import piano_roll as pr

    sub = args.piano_roll_command

    if sub == "add-notes":
        result = pr.add_notes_simple(
            client,
            pattern=args.pattern,
            note_names=args.notes,
            position=args.position,
            length=args.length,
            velocity=args.velocity,
        )
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Added {result.get('notes_added', 0)} notes to pattern {args.pattern}")
        return 0

    elif sub == "clear":
        result = pr.clear_notes(client, pattern=args.pattern)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Cleared notes from pattern {args.pattern}")
        return 0

    elif sub == "get-notes":
        result = pr.get_notes(client, pattern=args.pattern)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            notes = result.get("notes", [])
            print(f"Pattern {args.pattern}: {result.get('note_count', 0)} notes")
            print(f"\n{'Idx':>4} {'Note':<6} {'Name':<5} {'Pos':>6} {'Len':>6} {'Vel':>5}")
            print("-" * 35)
            for n in notes:
                name = pr.midi_to_note_name(n["note"])
                print(
                    f"{n['index']:>4} {n['note']:<6} {name:<5} "
                    f"{n['position']:>6} {n['length']:>6} {n['velocity']:>5}"
                )
        return 0

    elif sub == "quantize":
        result = pr.quantize(client, pattern=args.pattern, grid=args.grid)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Quantized pattern {args.pattern} to 1/{args.grid}")
        return 0

    elif sub == "transpose":
        result = pr.transpose(client, pattern=args.pattern, semitones=args.semitones)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            direction = "up" if args.semitones > 0 else "down"
            print(f"Transposed pattern {args.pattern} {abs(args.semitones)} semitones {direction}")
        return 0

    elif sub == "humanize":
        result = pr.humanize(client, pattern=args.pattern, amount=args.amount, seed=args.seed)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Humanized pattern {args.pattern} (amount={args.amount}, seed={args.seed})")
        return 0

    else:
        print(f"Unknown piano-roll command: {sub}", file=sys.stderr)
        return 1


def _cmd_plugins(client: DAWClient, args: argparse.Namespace) -> int:
    """Handle `toolshop daw plugins <subcommand>`."""
    from . import plugins as plugins_mod

    sub = args.plugins_command

    if sub == "list":
        result = plugins_mod.list_plugins()
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            if not result:
                print("No plugins found in standard directories.")
                print("Set FLSTUDIO_VST_PLUGINS env var for custom paths.")
            else:
                print(f"Found {len(result)} plugins:")
                print(f"\n{'Name':<30} {'Format':<8} {'Path'}")
                print("-" * 80)
                for p in result:
                    print(f"{p['name']:<30} {p['format']:<8} {p['path']}")
        return 0

    elif sub == "params":
        params = plugins_mod.get_all_params(client, track=args.track, slot=args.slot)
        if args.json:
            print(json.dumps(params, indent=2))
        else:
            print(f"Track {args.track} slot {args.slot}: {len(params)} params")
            print(f"\n{'Idx':>4} {'Name':<25} {'Value':>8}")
            print("-" * 40)
            for p in params:
                print(f"{p['index']:>4} {p['name']:<25} {p['value']:>8.3f}")
        return 0

    elif sub == "set-param":
        result = plugins_mod.set_param(
            client,
            track=args.track,
            slot=args.slot,
            param_index=args.param,
            value=args.value,
        )
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Track {args.track} slot {args.slot} param {args.param} = {args.value}")
        return 0

    else:
        print(f"Unknown plugins command: {sub}", file=sys.stderr)
        return 1


def _cmd_gen(client: DAWClient, args: argparse.Namespace) -> int:
    """Handle `toolshop daw gen <subcommand>`."""
    from . import generators as gen

    sub = args.gen_command

    if sub == "drum-pattern":
        result = gen.gen_drum_pattern(
            client,
            genre=args.genre,
            bars=args.bars,
            channel_kick=args.kick,
            channel_snare=args.snare,
            channel_hat=args.hat,
        )
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Generated {args.genre} drum pattern: {args.bars} bars")
            print(f"  Kick:  channel {args.kick}")
            print(f"  Snare: channel {args.snare}")
            print(f"  Hat:   channel {args.hat}")
        return 0

    elif sub == "chord-progression":
        result = gen.gen_chord_progression(
            client,
            pattern=args.pattern,
            key=args.key,
            scale=args.scale,
            progression=args.progression,
            bars=args.bars,
            chord_length=args.length,
        )
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Generated {args.progression} in {args.key} {args.scale}")
            print(f"  Pattern: {args.pattern}, Bars: {args.bars}, Notes: {result.get('notes_written', 0)}")
        return 0

    elif sub == "bassline":
        result = gen.gen_bassline(
            client,
            pattern=args.pattern,
            key=args.key,
            scale=args.scale,
            bars=args.bars,
            style=args.style,
            note_length=args.length,
        )
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Generated {args.style} bassline in {args.key} {args.scale}")
            print(f"  Pattern: {args.pattern}, Bars: {args.bars}, Notes: {result.get('notes_written', 0)}")
        return 0

    elif sub == "melody":
        result = gen.gen_melody(
            client,
            pattern=args.pattern,
            key=args.key,
            scale=args.scale,
            bars=args.bars,
            density=args.density,
            seed=args.seed,
        )
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Generated melody in {args.key} {args.scale} (density={args.density})")
            print(f"  Pattern: {args.pattern}, Bars: {args.bars}, Notes: {result.get('notes_written', 0)}")
        return 0

    elif sub == "arpeggio":
        result = gen.gen_arpeggio(
            client,
            pattern=args.pattern,
            chords=args.chords,
            pattern_type=getattr(args, "type", "up"),
            bars=args.bars,
            note_length=args.length,
            octave=args.octave,
        )
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Generated {getattr(args, 'type', 'up')} arpeggio: {args.chords}")
            print(f"  Pattern: {args.pattern}, Bars: {args.bars}, Notes: {result.get('notes_written', 0)}")
        return 0

    else:
        print(f"Unknown gen command: {sub}", file=sys.stderr)
        return 1


def _cmd_corpus(client: DAWClient, args: argparse.Namespace) -> int:
    """Handle `toolshop daw corpus <subcommand>`."""
    from . import corpus_intel as ci

    sub = args.corpus_command

    if sub == "suggest-bpm":
        result = ci.suggest_bpm(args.genre)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            src = result.get("source", "preset")
            sz = result.get("sample_size", 0)
            print(f"Suggested BPM for {args.genre}: {result.get('bpm', 140)} (source: {src}, n={sz})")
        return 0

    elif sub == "suggest-key":
        result = ci.suggest_key(args.genre)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            keys = result.get("keys", [])
            print(f"Suggested keys for {args.genre}: {', '.join(keys)}")
            print(f"  Primary: {result.get('primary', keys[0] if keys else '?')}")
        return 0

    elif sub == "suggest-arrangement":
        result = ci.suggest_arrangement(args.genre)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            arr = result.get("arrangement", [])
            print(f"Arrangement for {args.genre} (source: {result.get('source', '?')}):")
            print(f"\n{'Section':<12} {'Bars':>5}")
            print("-" * 20)
            for s in arr:
                print(f"{s['section']:<12} {s['bars']:>5}")
            stats = result.get("section_stats", [])
            if stats:
                print(f"\nCorpus section stats:")
                print(f"{'Type':<12} {'Count':>6} {'Avg Lines':>10}")
                print("-" * 30)
                for s in stats:
                    print(f"{s['section']:<12} {s['count']:>6} {s.get('avg_lines', 0):>10.1f}")
        return 0

    elif sub == "suggest-pattern":
        result = ci.suggest_pattern(args.genre)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Drum pattern for {args.genre}: {result.get('pattern', 'drill')}")
        return 0

    elif sub == "section-stats":
        result = ci.get_section_stats(args.genre)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            types = result.get("section_types", [])
            print(f"Section stats for {args.genre}: {result.get('total_sections', 0)} total sections")
            print(f"\n{'Type':<12} {'Count':>6} {'Avg Lines':>10} {'Avg Words':>10}")
            print("-" * 40)
            for s in types:
                print(f"{s['section']:<12} {s['count']:>6} {s.get('avg_lines', 0):>10.1f} {s.get('avg_words', 0):>10.1f}")
        return 0

    elif sub == "flow-to-midi":
        result = ci.flow_to_midi(args.lyrics_file)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            lines = result.get("lines", [])
            print(f"Flow analysis: {result.get('total_lines', 0)} lines, avg density {result.get('avg_note_density', 0)}/bar")
            print(f"\n{'Line':>4} {'Syl':>4} {'Grid':>6} {'Text'}")
            print("-" * 60)
            for l in lines:
                print(f"{l['line']:>4} {l['syllables']:>4} {l['grid']:>6} {l['text']}")
        return 0

    else:
        print(f"Unknown corpus command: {sub}", file=sys.stderr)
        return 1
