# Color Theory Principles for the Cat Bot
## Knowledge Document for Palette Tuning

Based on: Josef Albers "Interaction of Color" (1963), Johannes Itten "The Art of Color" (1961), James Gurney "Color and Light" (2010).

---

## Part 1 — The Most Important Rule (Albers)

> *"In visual perception a color is almost never seen as it really is. This fact makes color the most relative medium in art."*
> — Josef Albers

**A color never exists alone.** It always looks different depending on what surrounds it. A gray on a blue background looks reddish. The same gray on an orange background looks bluish.

**Consequence for the bot:** We cannot choose cat color, eye color, and background color independently. Each color always affects how the others are perceived.

```
Selection order:
  1. cat_hue  →  affects how the eyes and background are perceived
  2. eye_hue  →  small accent, less influence on surroundings
  3. bg_hue   →  strongly affects how the cat is perceived (large area)
```

---

## Part 2 — Itten: The Seven Color Contrasts

Johannes Itten identified seven types of color contrast. All seven can appear in a cat portrait.

### 2a. Light-Dark Contrast

The most important contrast for making the subject visible.

Each pure (saturated) color has an inherent lightness value (HSL-L). On a gray scale from white (0) to black (12):

```
Yellow         ≈ L 0.85   ← lightest pure color
Orange         ≈ L 0.70
Red            ≈ L 0.50
Green          ≈ L 0.50
Blue           ≈ L 0.35
Violet         ≈ L 0.25   ← darkest pure color
```

**Key rule:** Cool colors (blue, green) feel transparent and weightless — they are perceived as lighter than they actually are. Warm colors (red, orange) feel opaque and heavy — they are perceived as darker than they actually are.

**Consequence:** Cat and background MUST have sufficient L-contrast for the cat to be clearly visible. Minimum recommended ΔL ≥ 0.15 between cat and background.

### 2b. Cold-Warm Contrast

> *"Of all the seven color contrasts, the cold-warm contrast is the most sonorous."*
> — Itten

This is the most expressive contrast. It creates:
- Spatial depth (warm = near, cool = far)
- Emotional resonance (cool = calm, warm = energy)

Itten's poles are:
- **Warmest:** red-orange (minium) ~H ≈ 15–25°
- **Coldest:** blue-green (manganese oxide) ~H ≈ 165–180°

```
WARM side (hue degrees):
  Yellow:        H 45–65°
  Yellow-orange: H 30–45°
  Orange:        H 20–35°
  Red-orange:    H 10–25°    ← WARMEST POINT
  Red:           H 0° / 350–360°
  Red-violet:    H 320–350°

COOL side:
  Yellow-green:  H 65–100°
  Green:         H 100–140°
  Blue-green:    H 155–175°  ← COLDEST POINT
  Blue:          H 200–240°
  Blue-violet:   H 240–270°
  Violet:        H 270–300°
```

**Important:** A color is not absolutely cool or warm — it is cool/warm *relative to its neighbor*.
- Violet is warm next to blue
- Violet is cool next to red
- Green is cool next to orange, but warm next to blue

**Gurney confirms:** Top half of color wheel = warm (yellow-greens through reds). Bottom half = cool (blue-greens, blues, violets). Cool evokes winter, night, shadow, calm. Warm evokes fire, energy, appetite.

**Consequence:** Cold-warm contrast between cat and background gives the strongest visual tension. A warm cat on a cool background "jumps out" of the image.

### 2c. Contrast of Hue

Simplest and strongest with primary colors (yellow/red/blue). Weakens with secondary/tertiary colors.

**Rule of thumb:** For a color to look "true," surround it with:
- Its complementary color (opposite on the color wheel, ΔH ≈ 150–210°)
- Or a neutral background (gray/white/black)

### 2d. Contrast of Saturation (Itten contrast #6)

A highly saturated color placed next to a dull version of the same hue — or next to a neutral — creates saturation contrast.

Four ways to dull a color:
```
1. Mix with white       → tint  (cools and lightens; whitened reds go magenta)
2. Mix with black       → shade (deadens the color, makes it heavy)
3. Mix with gray        → tone  (neutralizes without strong light/dark shift)
4. Mix with complement  → chromatic gray (warm or cool depending on proportion)
```

**Key principles:**
- Dull tones "live" by virtue of vivid tones surrounding them — a muted color looks richer next to a pure one
- To express *pure* saturation contrast: use the same hue at different purity levels (intense red vs. dull red)
- Gray neutralizes strong colors into a quiet, harmonious effect

> *"More paintings fail because of too much intense color rather than too much gray."* — Gurney

**Direct validation for this bot:** Our background at S=25% (muted) deliberately exploits saturation contrast. The cat's higher S makes it look MORE vivid against the muted background. The background does not compete — it amplifies the cat.

### 2e. Contrast of Extension (Goethe via Itten)

Extension contrast is about area — how much space each color takes relative to its visual weight.

Goethe measured the inherent luminosity of pure colors (higher = brighter/lighter):
```
Yellow  = 9   ← brightest, lightest visual weight
Orange  = 8
Red     = 6
Green   = 6
Blue    = 4
Violet  = 3   ← darkest, heaviest visual weight
```

For two complementary colors to feel visually balanced, their areas are inversely proportional to their weights:
```
Yellow : Violet  = 1/4 : 3/4   (yellow is so bright it needs only a small area)
Orange : Blue    = 1/3 : 2/3
Red    : Green   = 1/2 : 1/2   (equal — they carry equal visual weight)
```

**Expression vs. harmony:**
- Harmonious proportions → quiet, stable, settled
- Non-harmonious proportions → expressive, dynamic, tension

**The minority color effect:** When a small area of vivid color is surrounded by large neutral area (like bright eyes on a mostly gray cat), the eye compensates — the small color appears *more intense* than if it occupied a larger area. This is why small, high-S eyes can still feel vivid and powerful.

---

## Part 3 — Simultaneous Contrast (Albers + Itten)

When two colors are placed side by side, each color "pushes" its neighbor toward its own complementary. This is called **simultaneous contrast**.

```
Examples:
  Blue background  →  gray cat looks reddish
  Orange cat       →  neutral eyes look bluish
  Green cat        →  neutral eyes look red-violet
```

**Complementary pairs (opposite on the color wheel):**
```
  Red    ↔  Green
  Orange ↔  Blue
  Yellow ↔  Violet
```

**Consequence for the eyes:** The eyes are a small accent on the cat's large surface. The cat's body color will "push" the perceived hue of the eyes toward the cat's complementary.

- Orange/red cat  →  blue/teal eyes look more intense (pushed toward blue)
- Green cat       →  orange/red eyes look more intense
- Blue/gray cat   →  gold/amber eyes look more intense

**Adding ΔL between two colors suppresses simultaneous effects** — this makes the ΔL ≥ 0.15 rule doubly important: it also reduces unwanted simultaneous contrast between cat and background.

---

## Part 4 — Lightness Rules for Pure Colors

**Yellow is the lightest pure color. Violet is the darkest.**

This means:
- A dark yellow = no longer a true yellow (black/gray has been added)
- A light blue = a pale, almost-white blue
- Saturated blue is already very dark (L ≈ 0.35)

**Background vs. foreground:**
```
Light cat (TONAL, L > 0.55):
  → Background should either:
     a) Have lower L (dark background → cat glows forward)
     b) Or have a strongly different hue (color contrast makes it visible regardless of L)

Dark cat (NOIR, L < 0.45):
  → Background should either:
     a) Have higher L (light background → cat reads as silhouette)
     b) Or have complementary color temperature (cool cat + warm light background)
```

**Itten says:** Compositions using cold-warm contrast are most beautiful when light-dark contrast is minimal (all colors at equal lightness). Then you see pure temperature contrast without noise.

---

## Part 5 — Harmony Models

### 5a. Classic Harmony Structures (Itten)

For a color combination to feel **harmonious**, it should satisfy one of these patterns:

```
COMPLEMENTARY — dyad (two colors, ΔH ≈ 180°):
  Examples: red+green, orange+blue, yellow+violet
  Mix to neutral gray → "balance for the eye"
  Static if used at harmonious area proportions;
  expressive if used at equal areas (against the proportions)

ANALOGOUS (neighboring hues, ΔH < 30°):
  Examples: blue + blue-green + green
  Calm, harmonious, low tension

TRIADIC (three colors, ΔH ≈ 120°):
  Strongest: yellow+red+blue (primary triad)
  Weaker:    orange+green+violet (secondary triad)
  Moodier variants: yellow-orange/red-violet/blue-green

SPLIT-COMPLEMENTARY (ΔH ≈ 150° to each side):
  Example: red with blue-green and yellow-green
  Exciting but not harsh — safer than straight complementary

TETRAD — two complementary pairs (square on wheel):
  Example: yellow/violet/red-orange/blue-green
  Complex — needs one dominant, three subordinate roles

HEXAD — three complementary pairs (hexagon on wheel):
  Yellow+violet / orange+blue / red+green = full spectrum
  Very complex — needs strong value hierarchy to read clearly
```

**Area proportions (Goethe) for complementary pairs — balanced use:**
```
  Yellow : Violet = 1 : 3
  Orange : Blue   = 1 : 2
  Red    : Green  = 1 : 1
```

### 5b. Gamut Thinking (Gurney)

A **gamut** is the total group of possible colors in a composition, shown as a polygon on the color wheel.

> *"Good color comes not just from what you include, but from what you LEAVE OUT."* — Gurney

**Key concepts:**

- **Subjective primaries** = the corner colors of the gamut polygon (the "parent" colors)
- **Subjective neutral** = the color at the geometric center of the gamut = the overall color cast. In a yellow-green gamut, even neutral strokes appear slightly greenish. This is the "key" of the image.
- **Saturation cost** = intermediate mixtures between two colors are always less saturated than either starting color. The secondaries of any scheme are necessarily duller than the primaries.

**Gamut shapes for cat portraits:**
```
MOOD AND ACCENT:
  One dominant cool hue family (cat body)
  + one small warm accent from across the wheel (eyes)
  Effect: unified, punchy, memorable
  → best for tonal/noir pairs where the eyes are the focal point

ATMOSPHERIC TRIAD (equilateral triangle shifted to one side of the wheel):
  Three hues all from the same temperature family
  Effect: moody, subjective, mysterious
  → good for collections with a dark, artistic feel

COMPLEMENTARY DIAMOND (stretches across wheel center):
  Warm hue ↔ cool hue, all tones/tints from both sides
  Effect: balanced, stable, energetic — the most common successful scheme
  → reliable choice for bright tonal cats
```

**Critical insight:** Within a controlled cool gamut, warm colors still appear warm in context. Relative contrast is enough — you don't need maximum temperature difference. As Gurney puts it: "the relative warm colors appear warm enough in the context of the picture."

---

## Part 6 — Direct Rules for the Cat Bot

### Rule 1: Cold-warm contrast gives the best results

```python
# Pseudocode
cat_is_warm = cat_hue < 60 or cat_hue > 300   # red, orange, yellow family
cat_is_cool = 100 < cat_hue < 280             # green, blue, violet family

if cat_is_warm:
    bg_should_be = "cool"   # H 100–240°, S=25% (already enforced)

if cat_is_cool:
    bg_should_be = "warm"   # H 0–60° or 300–360°, S=25%
```

### Rule 2: Eyes benefit from simultaneous contrast

```python
# After cat_hue is chosen:
# Eyes near the complementary of the cat look most intense

complementary_of_cat = (cat_hue + 180) % 360
# Eyes very close to complementary_of_cat (±30°) can "merge" into cat
# Eyes 60–150° away from cat_hue give stronger accent without clashing
```

### Rule 3: L-contrast is non-negotiable

Minimum ΔL between cat and background: **≥ 0.15**

```
Cat L=0.70 (light tonal)  →  Background L ≤ 0.55 for visibility
Cat L=0.30 (dark noir)    →  Background L ≥ 0.45 for visibility
```

### Rule 4: Background S=25% is strategically correct

Our muted background (S=25%) means:
- The background never competes with the cat
- The cat (higher S) always looks more vivid against the muted ground
- This is **contrast of saturation** (Itten contrast #6) in practice
- Confirmed by Gurney: "More paintings fail because of too much intense color rather than too much gray"

### Rule 5: Same-temperature combinations work, but require L-contrast

A warm cat on a warm background is not automatically bad — but then L-contrast must compensate. Two colors of the same temperature and same lightness literally blend together (Albers: they create a "middle mixture" illusion).

### Rule 6: Eyes are small — choose higher S than you think

Due to size-based chroma loss (Gurney Ch 8), small colored objects appear less saturated than large ones at the same S value. The minority color effect (Itten) makes them appear *more intense*, but only if they are already highly saturated.

**Rule:** Aim for eye S ≥ 0.65 for the eyes to read clearly. If you want vivid, jewel-like eyes (perceived S ≈ 0.80), set actual S ≈ 0.90.

### Rule 7: In multi-cat collections, order affects perception

Due to **successive contrast** (Gurney), looking at one color shifts how we see the next — the eye generates an afterimage in the complementary color.

```
In a 3-cat collection:
If katt_1 is strongly WARM (orange):
  → viewer's eye adapts to warm → katt_2 looks COOLER and more blue
  
If katt_1 is strongly COOL (blue):
  → viewer's eye adapts to cool → katt_2 looks WARMER

Strategy: place warm cat first, cool cat second
→ maximizes the perceived temperature contrast between them
```

### Rule 8: Green cats need warm accents

From Gurney's "Green Problem" (Ch 4): green is commercially risky — viewers are less attracted to strong green compositions.

Fix: add warm (reddish/orange) background OR warm eye accents to any green cat.
- Orange eyes on a green cat create complementary contrast AND counteract the "cold" commercial risk
- Think of it as "smuggling reds" into the composition (Gurney's phrase)

---

## Part 7 — Spatial Depth and Background Lightness (Itten)

Color alone creates an illusion of depth. The direction of the depth effect depends on the background tone.

**On a DARK background** (relevant for noir cats, dark bg):
```
Most advancing → yellow
                orange
                red-orange
                red
                green
                blue-green
                blue
Most receding  → violet
```

**On a LIGHT background** (relevant for tonal cats, light bg): the order REVERSES.
```
Most advancing → violet, blue
                blue-green
                green
                red
                orange
Most receding  → yellow (swallowed by the light background)
```

**Advancing force interacts with L-contrast:**
- Warm cat on dark background = **double advance** (warm advances on dark + light-on-dark)
- Cool cat on light background = **double advance** (cool advances on light + dark-on-light)
- Warm cat on light background = forces cancel → flat, ambiguous
- Cool cat on dark background = forces cancel → cat sinks into background

**This is why the tonal/noir system is correct:**
```
katt_1 = light (L > 0.55) + warm (H 0–60°) on a dark-ish cool bg → double advance ✓
katt_2 = dark  (L < 0.45) + cool (H 180–260°) on a light-ish warm bg → double advance ✓
```

---

## Part 8 — The Inherent Character of Colors (for mood selection)

From Itten, Goethe, and Gurney:

Goethe identified two fundamental poles:
```
"PLUS" SIDE (warm, advancing):    "MINUS" SIDE (cool, receding):
  Yellow, Orange, Red                Blue, Blue-violet, Violet
  → radiance, power, nobility        → deprivation, shadow, distance
  → warmth, closeness                → coldness, weakness, mystery
  → appetite, energy                 → serenity, meditation, calm
```

This is wired into human biology as **opponent process theory**: all color perception results from interactions between opposing pairs of receptors (blue/yellow, green/red, light/dark).

```
WARM COLORS (H 0–60°, 300–360°):
  → Near, heavy, stimulating, earthy, active
  → Look darker than they are
  → Yellow: bright, intellectual, warm, fastest-seen color
  → Orange: appetite, warmth, energy (used by fast food deliberately)
  → Red: blood, passion, power, anger

COOL COLORS (H 100–260°):
  → Far, light, calming, airy, passive
  → Look lighter than they are
  → Blue: dark in reality, perceived as "lightweight"
  → Blue-green: coldest point, most receding hue
  → Violet: dark and mysterious, smallest visual weight

NEUTRAL TONES (gray, S 0–15%):
  → Have no character of their own
  → Always take color from their neighbors (simultaneous contrast)
  → Our background (S=25%) is "almost neutral" — acts as an empty canvas
```

---

## Part 9 — Visual Perception Effects (Gurney Ch 8)

### 9a. Color Constancy

> *Color constancy* refers to our automatic habit of interpreting local colors as stable and unchanging, regardless of surrounding context or illumination.

A fire truck looks red under orange firelight, blue twilight, or fluorescent light. Our visual systems infer the "true" color from context and memory of known objects.

**For digital cat art:**
- Viewers' brains will partially correct for context shifts — a background hue won't completely override the cat's perceived color
- BUT a highly saturated background (S ≫ 25%) can overwhelm color constancy and significantly distort the perceived cat color
- This is another validation of S=25% muted backgrounds — they are below the threshold that overwhelms constancy

### 9b. The Five Factors That Affect Color Appearance

From Gurney's synthesis of visual perception research:

```
1. SIMULTANEOUS CONTRAST
   Background hue/saturation induces opposite qualities in the foreground object.
   (blue bg makes orange look more orange, etc.)

2. SUCCESSIVE CONTRAST
   Looking at one color shifts how you see the next.
   (afterimage in the complementary color loads the eye temporarily)

3. CHROMATIC ADAPTATION
   The visual system adapts to a dominant color temperature over time,
   like a camera's auto-white-balance. A strongly warm color scheme
   will adapt your eye to warm — making neutral objects appear slightly cool.

4. COLOR CONSTANCY
   Known objects are perceived as their "true" local color regardless of
   lighting or context. Partially overrides the effects above.

5. SIZE OF OBJECT
   Smaller colored objects lose apparent chroma.
   A 5px eye spot appears less saturated than a 200px cat body at the same S value.
```

### 9c. Practical Compensation

```
Eyes (small area):
  → Boost S: aim for actual S ≥ 0.65, even if target perceived S is ~0.50
  → The minority color effect (Itten 2e) will amplify intensity,
     but only if the base S is already high

Multi-cat collections (successive contrast):
  → Alternate warm/cool between cat_1 and cat_2 in each pair
  → Place warm cat first: viewer's eye loads with warm adaptation
    → cool cat_2 appears COOLER than actual S would suggest
  → This maximizes perceived temperature contrast for free

Background saturation:
  → Keep bg S ≤ 0.30 to avoid overwhelming color constancy
  → Above S=0.40 background risk distorting the cat's perceived hue
```

---

## Part 10 — Code Implementation

### Problem with the current system:
Cat, eyes, and background are chosen independently. But:
- The background strongly affects how the cat is perceived
- The cat's color shifts the perceived hue of the eyes
- Small areas (eyes) lose chroma at viewing distance
- Multi-cat compositions have successive contrast effects

### Recommended selection order:
1. **Choose the cat color first** (hue + lightness → tonal vs. noir)
2. **Filter background based on cat temperature** (warm cat → prefer cool bg-hue)
3. **Verify L-contrast** between cat and background ≥ 0.15
4. **Filter eyes based on cat color** (prefer eyes 60–180° away from cat's hue)
5. **Boost eye S slightly** to compensate for size-based chroma loss

### HSL-based implementation sketch:

```python
def temperature(hue):
    """Returns 'warm', 'cool', or 'neutral'."""
    if hue < 60 or hue > 300:
        return 'warm'
    elif 100 < hue < 260:
        return 'cool'
    else:
        return 'neutral'  # yellow-green and red-violet zone

def l_contrast_ok(cat_l, bg_l, min_delta=0.15):
    return abs(cat_l - bg_l) >= min_delta

def eye_is_accent(cat_hue, eye_hue):
    """Eyes 60–180° from cat hue give the strongest accent."""
    delta = abs((eye_hue - cat_hue + 180) % 360 - 180)
    return 60 <= delta <= 180  # avoid too analogous (< 60°)

def eye_s_adjusted(target_perceived_s):
    """Small objects lose chroma — boost S slightly to compensate."""
    return min(1.0, target_perceived_s * 1.15)
```

---

## Summary in One Sentence

**A warm, medium-light (tonal) cat on a cool, muted (S=25%) background — with high-S eyes in the complementary direction (ΔH 60–180° from cat hue), and a minimum ΔL of 0.15 between cat and background — will almost always produce a harmonious and visually strong result.**

But remember Albers: no color is "correct" in isolation. Always evaluate the combination as a whole. The background changes the cat. The cat changes the eyes. The eyes anchor the whole composition.
