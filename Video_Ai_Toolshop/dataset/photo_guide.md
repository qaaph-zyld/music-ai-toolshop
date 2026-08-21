# Photo Guide: 25-30 Images for Character LoRA Training

This guide describes exactly what photos to take (or select from existing photos) to "scan" a person's face and identity into an AI LoRA model. Each image has a specific purpose — together they teach the model the person's facial structure, skin texture, hair, expressions, and how they look under different lighting and angles.

## General Rules (Apply to ALL Photos)

- **Resolution:** At least 1024×1024 pixels (phone photos are fine — modern phones shoot 4000×3000+)
- **Face visibility:** Face must be clearly visible — no sunglasses, no hands covering face, no heavy shadows across features
- **Sharpness:** No motion blur. If using phone, tap to focus on the face before shooting
- **One person only:** No other people in the frame. The subject should be the only face visible
- **Recent:** All photos from the same time period (within ~6 months) — no childhood photos mixed with adult photos
- **No filters:** No Instagram filters, no beauty mode, no portrait mode background blur. Raw photos only
- **No heavy makeup changes:** If the person wears makeup, keep it consistent across most shots. A few no-makeup shots are good for variety
- **Distance:** Face should fill 30-80% of the frame depending on the shot type (see below)
- **Format:** JPG or PNG. Phone HEIC is fine (will be converted during processing)

---

## Category A: Core Angles (10 images)

These are the most important photos. They teach the model the person's facial geometry from every standard angle.

### Image 1: Front-Facing, Neutral Expression, Indoor
- **Angle:** Directly front-facing, camera at eye level
- **Expression:** Neutral, relaxed face, mouth closed, eyes open normally
- **Lighting:** Soft, even lighting — stand facing a window during daytime, or use a ring light
- **Distance:** Face fills ~60% of frame (waist-up shot)
- **Background:** Plain wall, uncluttered
- **Purpose:** Teaches the model the baseline front-view facial structure
- **How to shoot:** Stand 1-1.5m from subject, hold phone/camera at their eye height, ask them to look directly into lens

### Image 2: Front-Facing, Slight Smile, Indoor
- **Angle:** Directly front-facing, camera at eye level
- **Expression:** Natural slight smile — not forced, not a grin. Slight teeth showing is fine
- **Lighting:** Same soft even lighting as Image 1
- **Distance:** Same as Image 1 (waist-up)
- **Background:** Plain wall
- **Purpose:** Teaches how the face changes when smiling — cheek elevation, lip shape, eye crinkling
- **How to shoot:** Ask them to think of something funny, or say "smile with your eyes"

### Image 3: 3/4 Angle Left, Neutral
- **Angle:** Subject turned ~30-45° to their left (their left ear moves away from camera). Camera stays front
- **Expression:** Neutral
- **Lighting:** Soft even lighting
- **Distance:** Face fills ~50% of frame (waist-up to chest-up)
- **Background:** Plain or simple
- **Purpose:** Teaches the side contour of the face — jaw line, cheekbone, nose bridge from a 3/4 view
- **How to shoot:** Ask subject to turn their body 45° left but keep eyes on camera

### Image 4: 3/4 Angle Right, Neutral
- **Angle:** Subject turned ~30-45° to their right (mirror of Image 3)
- **Expression:** Neutral
- **Lighting:** Soft even lighting
- **Distance:** Same as Image 3
- **Background:** Plain or simple
- **Purpose:** Teaches the opposite side contour — faces are NOT symmetrical, the model needs both sides
- **How to shoot:** Ask subject to turn body 45° right, eyes on camera

### Image 5: Side Profile Left, Full
- **Angle:** Subject turned 90° to their left — full side profile facing camera
- **Expression:** Neutral, mouth closed
- **Lighting:** Soft even or slightly directional from the front
- **Distance:** Face fills ~40% of frame (head-and-shoulders)
- **Background:** Plain
- **Purpose:** Teaches the exact side profile — nose shape, chin, forehead slope, ear position
- **How to shoot:** Subject turns fully sideways, looks straight ahead (not at camera)

### Image 6: Side Profile Right, Full
- **Angle:** Subject turned 90° to their right — mirror of Image 5
- **Expression:** Neutral, mouth closed
- **Lighting:** Soft even
- **Distance:** Same as Image 5
- **Background:** Plain
- **Purpose:** Teaches right-side profile (asymmetry capture)
- **How to shoot:** Subject turns fully right, looks straight ahead

### Image 7: Slightly Above, Front-Facing
- **Angle:** Camera positioned ~20° above subject's eye level, shooting down slightly. Subject looks up at camera
- **Expression:** Neutral
- **Lighting:** Natural — shoot outdoors on an overcast day or indoors with ceiling light
- **Distance:** Face fills ~50% of frame (chest-up)
- **Background:** Simple
- **Purpose:** Teaches how the face looks from a higher angle — forehead prominence, under-chin area, eye shape from above
- **How to shoot:** Photographer stands, subject sits. Or hold camera slightly above your own head and tilt down

### Image 8: Slightly Below, Front-Facing
- **Angle:** Camera positioned ~20° below subject's eye level, shooting up slightly. Subject looks down at camera
- **Expression:** Neutral
- **Lighting:** Natural
- **Distance:** Face fills ~50% of frame (chest-up)
- **Background:** Simple, ideally sky or ceiling
- **Purpose:** Teaches jaw line from below, nostril shape, chin prominence
- **How to shoot:** Subject stands, photographer sits or crouches. Subject looks down into lens

### Image 9: Tilted Head Left, Front-Facing
- **Angle:** Front-facing but subject tilts head ~15-20° to their left (like a curious dog look)
- **Expression:** Slight smile or neutral
- **Lighting:** Soft even
- **Distance:** Face fills ~60% of frame
- **Background:** Plain
- **Purpose:** Teaches facial asymmetry under head tilt — how features shift when the head isn't level
- **How to shoot:** Ask subject to "tilt your head like you're curious about something"

### Image 10: Tilted Head Right, Front-Facing
- **Angle:** Front-facing, head tilted ~15-20° to their right (mirror of Image 9)
- **Expression:** Slight smile or neutral
- **Lighting:** Soft even
- **Distance:** Same as Image 9
- **Background:** Plain
- **Purpose:** Opposite-side tilt asymmetry
- **How to shoot:** Mirror of Image 9

---

## Category B: Expressions (6 images)

These teach the model how the person's face moves — crucial for generating natural-looking video clips later.

### Image 11: Big Genuine Laugh
- **Angle:** Front-facing, eye level
- **Expression:** Full genuine laugh or big smile with teeth showing, eyes crinkled
- **Lighting:** Natural daylight
- **Distance:** Face fills ~60% of frame
- **Background:** Any
- **Purpose:** Teaches extreme expression — how cheeks bulge, eyes narrow, mouth opens when laughing
- **How to shoot:** Tell a joke or show a funny video. Capture the natural laugh, not a posed one

### Image 12: Serious / Intense Look
- **Angle:** 3/4 angle left
- **Expression:** Serious, intense, focused — like staring at something important. No smile. Slight squint
- **Lighting:** Slightly dramatic — one side brighter than the other (window light from one side)
- **Distance:** Face fills ~60% of frame (chest-up)
- **Background:** Darker or blurred
- **Purpose:** Teaches the "cinematic serious" look — jaw tension, brow furrow, eye intensity
- **How to shoot:** Ask them to "look at the camera like you're in a movie poster"

### Image 13: Surprised
- **Angle:** Front-facing
- **Expression:** Genuine surprise — eyebrows raised, eyes wide, mouth slightly open
- **Lighting:** Even
- **Distance:** Face fills ~55% of frame
- **Background:** Any
- **Purpose:** Teaches raised-brow facial dynamics, eye widening
- **How to shoot:** Surprise them — clap loudly, or ask them to fake the most surprised face they can

### Image 14: Thoughtful / Pensive
- **Angle:** 3/4 angle right, looking away from camera
- **Expression:** Thoughtful — eyes looking off into distance, slight lip compression, relaxed brow
- **Lighting:** Soft window light from the side they're facing
- **Distance:** Face fills ~40% of frame (head-and-shoulders)
- **Background:** Window or outdoor
- **Purpose:** Teaches the "thinking" micro-expression — subtle lip press, eye direction, relaxed but engaged face
- **How to shoot:** Ask them to "look out the window and think about something important"

### Image 15: Talking / Mid-Speech
- **Angle:** Front-facing or 3/4
- **Expression:** Mid-sentence — mouth open as if speaking, natural hand gesture if visible
- **Lighting:** Natural
- **Distance:** Face fills ~50% of frame (chest-up)
- **Background:** Any
- **Purpose:** Teaches mouth shapes during speech — important for video generation (even though we suppress talking in generation, the model needs to know the mouth shapes)
- **How to shoot:** Record a video of them talking naturally, then extract a frame mid-sentence. Or have them talk and snap photos

### Image 16: Relaxed / Casual Smile
- **Angle:** 3/4 angle left
- **Expression:** Relaxed, casual, half-smile — like they just heard something mildly amusing
- **Lighting:** Outdoor natural light (golden hour if possible)
- **Distance:** Face fills ~40% of frame (upper body)
- **Background:** Outdoor — trees, buildings, anything natural
- **Purpose:** Teaches the "candid" look — relaxed facial muscles, natural micro-expression
- **How to shoot:** Walk with them outdoors, have a conversation, snap photos mid-conversation

---

## Category C: Lighting Variety (6 images)

These teach the model how the person's face responds to different lighting — critical for cinematic generation later.

### Image 17: Harsh Direct Sunlight
- **Angle:** Front-facing
- **Expression:** Neutral or slight squint (natural reaction to sun)
- **Lighting:** Direct midday sun — hard shadows on face, high contrast
- **Distance:** Face fills ~50% of frame
- **Background:** Outdoor
- **Purpose:** Teaches skin texture under harsh light — pores, blemishes, shadow patterns. The model needs to know the person's skin isn't smooth plastic
- **How to shoot:** Stand outside at noon, face the sun. Don't use phone HDR (turn it off for this one shot)

### Image 18: Golden Hour Backlit
- **Angle:** 3/4 angle, subject facing the sunset
- **Expression:** Relaxed
- **Lighting:** Golden hour (1 hour before sunset) — warm orange light hitting face from the side, rim light on hair
- **Distance:** Face fills ~35% of frame (upper body, include hair)
- **Background:** Sky, landscape
- **Purpose:** Teaches warm color cast on skin, hair rim lighting, golden hour glow
- **How to shoot:** 1 hour before sunset, position subject so sun is to their side/back. Expose for the face

### Image 19: Indoor Low Light / Moody
- **Angle:** 3/4 angle left
- **Expression:** Neutral or serious
- **Lighting:** Single lamp or window in a dark room — strong directional light from one side, deep shadow on the other (chiaroscuro)
- **Distance:** Face fills ~60% of frame
- **Background:** Dark room
- **Purpose:** Teaches how the face looks in dramatic low-key lighting — shadow shapes, highlight areas
- **How to shoot:** At night, turn off all lights except one lamp. Position lamp 45° to subject's left. Shoot

### Image 20: Overcast / Soft Diffused
- **Angle:** Front-facing
- **Expression:** Neutral
- **Lighting:** Overcast day outdoors — completely flat, even, shadowless light
- **Distance:** Face fills ~55% of frame
- **Background:** Any outdoor
- **Purpose:** Teaches the "true" skin tone under neutral light — no color cast, no shadows. This is the reference for color accuracy
- **How to shoot:** Go outside on a cloudy day. Face the sky (not the ground). Shoot

### Image 21: Neon / Colored Light
- **Angle:** Front-facing or 3/4
- **Expression:** Neutral
- **Lighting:** Colored light source — neon sign, LED strip, or colored gel over a lamp. Blue, pink, or teal preferred
- **Distance:** Face fills ~50% of frame
- **Background:** Dark with colored light source visible
- **Purpose:** Teaches how skin responds to colored light — color spill, reflection patterns. Crucial for cinematic night scenes
- **How to shoot:** Find a neon sign at night, or buy a cheap LED strip ($5). Hold it near the face and shoot

### Image 22: Mixed Indoor / Outdoor
- **Angle:** 3/4 angle
- **Expression:** Natural
- **Lighting:** Standing half in, half out of a doorway — one side lit by outdoor daylight, other side in indoor tungsten light
- **Distance:** Face fills ~40% of frame (upper body)
- **Background:** Doorway / threshold
- **Purpose:** Teaches mixed color temperature handling — how the person's skin looks under both warm and cool light simultaneously
- **How to shoot:** Have subject stand in a doorway at noon, one shoulder outside, one inside. Shoot from the side

---

## Category D: Distance & Framing (4 images)

These teach the model what the person looks like at different distances — important for generating full-body or wide shots.

### Image 23: Extreme Close-Up (Face Only)
- **Angle:** Front-facing
- **Expression:** Neutral
- **Lighting:** Soft even
- **Distance:** Face fills 90-100% of frame — just face, maybe top of shoulders visible at bottom edge
- **Background:** Out of focus or edge of frame
- **Purpose:** Teaches fine skin detail — pores, eyebrow hair, eyelash length, skin texture around eyes and mouth
- **How to shoot:** Move close (30-50cm from face). If phone, use 2x zoom to avoid lens distortion. Do NOT use portrait mode

### Image 24: Head and Shoulders
- **Angle:** 3/4 angle left
- **Expression:** Slight smile
- **Lighting:** Soft window light
- **Distance:** Face fills ~35% of frame — head and shoulders visible, cuts off at upper chest
- **Background:** Blurred interior
- **Purpose:** Teaches neck and shoulder proportions, hair-to-shoulder ratio
- **How to shoot:** Stand 1m away, frame from top of head to mid-chest

### Image 25: Upper Body (Waist-Up)
- **Angle:** Front-facing
- **Expression:** Natural
- **Lighting:** Outdoor natural
- **Distance:** Face fills ~20% of frame — waist up, including torso and arms
- **Background:** Outdoor or interesting interior
- **Purpose:** Teaches body proportions, shoulder width, arm thickness, clothing fit
- **How to shoot:** Stand 2-3m away, frame from top of head to waist

### Image 26: Full Body (Standing)
- **Angle:** Front-facing, camera at waist level (not eye level)
- **Expression:** Natural, relaxed pose
- **Lighting:** Outdoor daylight
- **Distance:** Full body visible — head to feet. Face fills ~10% of frame
- **Background:** Outdoor — street, park, building
- **Purpose:** Teaches full body proportions — height, leg length, posture, stance. Important for generating walking/movement video clips
- **How to shoot:** Stand 4-5m away, hold camera at waist height (not eye height — eye height distorts body proportions). Shoot full body

---

## Category E: Variation Wildcards (4 images)

These add variety to prevent the model from overfitting to a specific look.

### Image 27: Different Hair / Headwear
- **Angle:** Front-facing
- **Expression:** Natural
- **Lighting:** Any
- **Distance:** Face fills ~50% of frame
- **Details:** Hair styled differently than other photos (wet hair, different part, ponytail, hat, beanie, hood). If the person never changes hair, just use a hat or hood
- **Purpose:** Teaches the model that hair is not a fixed feature — prevents it from baking a specific hairstyle into the LoRA
- **How to shoot:** Grab a hat, beanie, or hoodie. Put it on. Shoot

### Image 28: Different Outfit / Texture
- **Angle:** 3/4 angle
- **Expression:** Natural
- **Lighting:** Any
- **Distance:** Face fills ~35% of frame (upper body showing clothing)
- **Details:** Wearing something visually distinct from all other photos — leather jacket, knit sweater, patterned shirt, formal suit. Different texture and color from other outfits
- **Purpose:** Prevents the model from associating the person with a specific clothing style
- **How to shoot:** Change into a distinctly different outfit. Shoot

### Image 29: Action / Movement
- **Angle:** Any
- **Expression:** Natural, mid-action
- **Lighting:** Outdoor
- **Distance:** Face fills ~30% of frame (upper body to full body)
- **Details:** Subject in motion — walking, turning around, reaching for something, mid-step. Slight motion blur on the body is acceptable but face should be sharp
- **Purpose:** Teaches how the face looks during movement — dynamic expressions, hair in motion, body language
- **How to shoot:** Have them walk toward you while you shoot. Or have them turn around quickly and capture mid-turn

### Image 30: Candid / Unposed
- **Angle:** Any
- **Expression:** Whatever they're naturally doing
- **Lighting:** Any
- **Distance:** Any
- **Details:** Subject not aware of camera (or pretending not to be). Looking at phone, reading, eating, talking to someone else, working. The most natural photo in the set
- **Purpose:** Teaches the "at rest" face — when no one is performing for a camera. This is how the person actually looks in real life, which is what we want the AI to generate
- **How to shoot:** Have them do something (read a book, scroll phone, eat). Wait 2-3 minutes until they forget about the camera. Shoot

---

## Summary Checklist

| # | Category | Angle | Expression | Lighting | Distance |
|---|----------|-------|------------|----------|----------|
| 1 | Core | Front | Neutral | Soft indoor | Waist-up |
| 2 | Core | Front | Slight smile | Soft indoor | Waist-up |
| 3 | Core | 3/4 left | Neutral | Soft indoor | Waist-up |
| 4 | Core | 3/4 right | Neutral | Soft indoor | Waist-up |
| 5 | Core | Profile left | Neutral | Soft | Head-shoulders |
| 6 | Core | Profile right | Neutral | Soft | Head-shoulders |
| 7 | Core | Above | Neutral | Natural | Chest-up |
| 8 | Core | Below | Neutral | Natural | Chest-up |
| 9 | Core | Front, tilt L | Slight smile | Soft | Waist-up |
| 10 | Core | Front, tilt R | Slight smile | Soft | Waist-up |
| 11 | Expression | Front | Big laugh | Natural | Waist-up |
| 12 | Expression | 3/4 left | Serious | Dramatic | Chest-up |
| 13 | Expression | Front | Surprised | Even | Waist-up |
| 14 | Expression | 3/4 right, away | Thoughtful | Window | Head-shoulders |
| 15 | Expression | Front | Talking | Natural | Chest-up |
| 16 | Expression | 3/4 left | Casual smile | Golden hour | Upper body |
| 17 | Lighting | Front | Neutral/squint | Harsh sun | Chest-up |
| 18 | Lighting | 3/4 | Relaxed | Golden hour | Upper body |
| 19 | Lighting | 3/4 left | Neutral | Low key lamp | Chest-up |
| 20 | Lighting | Front | Neutral | Overcast | Chest-up |
| 21 | Lighting | Front | Neutral | Neon/colored | Chest-up |
| 22 | Lighting | 3/4 | Natural | Mixed temp | Upper body |
| 23 | Distance | Front | Neutral | Soft | Extreme close-up |
| 24 | Distance | 3/4 left | Slight smile | Window | Head-shoulders |
| 25 | Distance | Front | Natural | Outdoor | Waist-up |
| 26 | Distance | Front | Natural | Outdoor | Full body |
| 27 | Wildcard | Front | Natural | Any | Chest-up (hat/hood) |
| 28 | Wildcard | 3/4 | Natural | Any | Upper body (diff outfit) |
| 29 | Wildcard | Any | Mid-action | Outdoor | Upper body |
| 30 | Wildcard | Any | Candid | Any | Any |

## Common Mistakes to Avoid

- **Too many similar photos:** 15 front-facing photos with the same expression and lighting = the model overfits. Variety is more important than quantity
- **All photos from one day:** Shoot across 2-3 different days/sessions. Slight variation in skin, hair, and mood improves the LoRA
- **Heavy makeup in all photos:** If the person always wears the same makeup, the LoRA will bake it in. Include at least 3-4 no-makeup or minimal-makeup shots
- **Background too busy:** The model may learn to associate the person with the background. Keep at least 15 photos with plain or simple backgrounds
- **Low resolution screenshots:** Don't use screenshots from video calls or social media. Use original photo files
- **Eyes closed:** At least 25 of the 30 photos should have eyes clearly open and visible. 1-2 with blink/closed eyes is fine for variety
- **Same clothing in all photos:** Change shirts between sessions. The model can accidentally learn "this person always wears blue"
