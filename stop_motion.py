import glob
import os
from typing import Iterable

import imageio.v2 as imageio
import streamlit as st
from PIL import Image

# --- CONFIGURATION ---
IMAGE_DIR: str = "images"
THUMB_DIR: str = "thumbs"
THUMB_SIZE: tuple[int, int] = (250, 250)

os.makedirs(THUMB_DIR, exist_ok=True)


# --- HELPER FUNCTIONS ---
def make_thumbnail(img_path: str) -> str:
    """Create a thumbnail for an image if it doesn't exist."""
    thumb_path = os.path.join(THUMB_DIR, os.path.basename(img_path))
    if not os.path.exists(thumb_path):
        with Image.open(img_path) as im:
            im.thumbnail(THUMB_SIZE)
            im.save(thumb_path)
    return thumb_path


def generate_video(
    image_paths: Iterable[str], durations: Iterable[int], output_path: str
) -> None:
    """Generate a video from a sequence of images and their durations."""
    valid_durations = [d for d in durations if d > 0]
    if not valid_durations:
        st.error("Cannot generate video with zero duration for all frames.")
        return

    frame_duration_ms = 40
    fps = 1000.0 / frame_duration_ms

    writer = imageio.get_writer(output_path, fps=fps)
    for path, duration in zip(image_paths, durations):
        img = imageio.imread(path)
        num_frames = max(1, duration // frame_duration_ms)
        for _ in range(num_frames):
            writer.append_data(img)
    writer.close()


# --- STREAMLIT UI ---
st.title("Image Sequence to MP4")

image_files: list[str] = sorted(glob.glob(os.path.join(IMAGE_DIR, "*")))

if not image_files:
    st.warning(f"No images found in the '{IMAGE_DIR}' directory.")
    st.stop()


# --- STATE INITIALIZATION & CALLBACKS ---

# Initialize state for each image if not already present
for i, path in enumerate(image_files):
    if f"use_{i}" not in st.session_state:
        st.session_state[f"use_{i}"] = True
    if f"dur_{i}" not in st.session_state:
        st.session_state[f"dur_{i}"] = 200


def get_selected_indices_and_durations() -> tuple[list[int], list[int]]:
    """Get the indices and durations of the selected images."""
    indices = [i for i, _ in enumerate(image_files) if st.session_state[f"use_{i}"]]
    durations = [st.session_state[f"dur_{i}"] for i in indices]
    return indices, durations


def update_total_duration() -> None:
    """Callback to update the total duration from the sum of individual durations."""
    _, durations = get_selected_indices_and_durations()
    st.session_state.total_duration = sum(durations)


def rescale_individual_durations() -> None:
    """Callback to rescale individual durations when the total duration is changed."""
    indices, durations = get_selected_indices_and_durations()
    if not indices:
        return

    current_total = sum(durations)
    target_total = st.session_state.total_duration

    if current_total == 0:
        new_duration = target_total // len(indices) if indices else 0
        for i in indices:
            st.session_state[f"dur_{i}"] = new_duration
    else:
        scale = target_total / current_total
        for i in indices:
            st.session_state[f"dur_{i}"] = int(st.session_state[f"dur_{i}"] * scale)


# Initialize total duration on the first run
if "total_duration" not in st.session_state:
    update_total_duration()


# --- SIDEBAR ---
st.sidebar.header("Controls")
st.sidebar.number_input(
    "Total video duration (ms)",
    min_value=100,
    key="total_duration",
    on_change=rescale_individual_durations,
)

# --- MAIN UI ---
st.write("### Select Images and Durations")

selections: list[tuple[str, int]] = []
for i, path in enumerate(image_files):
    cols = st.columns([1, 1, 1])
    with cols[0]:
        st.image(
            make_thumbnail(path),
            caption=os.path.basename(path),
            use_container_width=True,
        )
    with cols[1]:
        st.checkbox("Include", key=f"use_{i}", on_change=update_total_duration)
    with cols[2]:
        st.number_input(
            "Duration (ms)",
            min_value=1,
            key=f"dur_{i}",
            step=25,
            on_change=update_total_duration,
        )

    if st.session_state[f"use_{i}"]:
        selections.append((path, st.session_state[f"dur_{i}"]))


# --- VIDEO GENERATION ---
if selections:
    paths, durations = zip(*selections)
    st.success(
        f"{len(paths)} images selected for a total duration of {sum(durations)} ms."
    )

    output_path = "output.mp4"
    if os.path.exists(output_path):
        with open(output_path, "rb") as f:
            st.video(f.read())

    if st.button("Generate Video"):
        generate_video(paths, durations, output_path)
        # Rerun to display the new video
        st.rerun()
else:
    st.info("No images selected.")
