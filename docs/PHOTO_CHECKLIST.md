# Tray photo checklist

> The project is now run by one person, so the training images are being made with the Gemini app instead, using the prompts in `docs/GENERATED_PHOTOS.md`. This checklist still applies to any real phone photos taken for testing.

This checklist explains how to take the photos that teach BuffetIQ's camera model to judge how full a buffet tray is. The model learns only from these photos, so their variety matters more than their number: photos that differ in tray, food, light, background and angle give a model that works in the demo, while 200 near-identical photos give one that does not.

## What you need

You need four containers, about 200 photos in total, and one to two hours across a few sessions. Use four containers that look like buffet trays, such as a deep metal tray, a shallow baking tray, a disposable foil tray (sold at Daiso and supermarkets for about S$2) and a rectangular plastic food container. Fill them mostly with dry props that keep for weeks, such as uncooked rice, dry noodles, cereal and bread or pastry, and use one real cooked dish (such as scrambled eggs) for some of the photos, so the model also sees real food.

## The four levels

Judge the level by how much of the tray's food is left, looking from above as a runner would.

| Level | Folder | What it looks like |
| --- | --- | --- |
| Empty | `tray_photos/empty/` | No food, or only crumbs, smears and a few scattered pieces |
| Low | `tray_photos/low/` | Some food left, but under a quarter of the tray |
| Half | `tray_photos/half/` | Between a quarter and three quarters of the tray |
| Full | `tray_photos/full/` | More than three quarters of the tray, as when a fresh batch goes out |

Skip a photo if you cannot decide between two levels (for example a tray exactly a quarter full), because unclear examples teach the model to guess.

## How many

Take at least 50 photos per level, 200 in total, and aim for 60 per level so that a few can be discarded. Keep the four levels roughly equal, within 10 photos of each other.

## Variety to include

Spread the photos across all of these, so that no tray, food, room or light appears in only one level:

1. Every container at every level, and every prop at every level.
2. At least three places, such as a kitchen counter, a wooden table and a table with a cloth.
3. At least three kinds of light, such as daylight from a window, ceiling lights and a dim or warm lamp.
4. Different heights and angles: mostly straight down from 30 to 60 cm above, as the runner will hold the phone, and some tilted up to about 30 degrees.
5. Food spread evenly, piled on one side and scattered, at the same level.
6. Some photos with a serving spoon or tongs in the tray.
7. Different phones, if more than one group member can shoot.

## What to avoid

1. Do not use the flash; the app tells runners to keep it off, so the model should learn without it.
2. Do not take bursts of almost the same photo. Change something (the angle, the arrangement or the light) between shots.
3. Keep the whole tray in the frame, filling most of the photo.
4. Do not include faces, name tags, real hotel logos or other people's food.
5. Use the normal photo mode, with no portrait mode, filters or zoom beyond 2x.

## Saving the photos

Name each photo with the session first, such as `s1_001.jpg` for the first session and `s2_001.jpg` for the second, so that we can tell sessions apart. Move the photos to the laptop (AirDrop works from an iPhone) and put each into its level's folder inside `Documents/BuffetIQ/tray_photos/`. iPhone HEIC photos are fine; the app converts them. The photos stay on the laptop because git ignores them; for training in Colab, we will upload them as a zip file.

## Check your photos

From the `src` folder, run this to count the photos per level and flag any problems:

```bash
python -m buffetiq.camera check
```

Once every level has at least 50 photos, the model can be trained (see `notebooks/01_train_camera_model.ipynb`).
