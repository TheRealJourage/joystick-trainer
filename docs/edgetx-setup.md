# EdgeTX setup on the Pocket (Master side)

Menu names are from the EdgeTX manual (color/BW radio pages). The Pocket has a monochrome
screen, so menu layout may differ slightly; names below are the option names the manual uses.
Not yet tried on the radio.

## 1. Model: receive the Pi on the jack

1. Model Setup > Trainer > mode **Master / Jack**.
2. **Ch. Range**: set to CH1-CH8 (the manual recommends channel 10 as the last channel at most).
3. **PPM frame**: leave defaults first (frame 22.5 ms, stop 300 us). The Pi side defaults match
   (`frame_us: 22500`, `pulse_us: 300`). Set polarity to match `active_high` in the Pi config.

## 2. Radio: which student channel drives which control

Radio settings > Trainer. One row per control, default mode is Replace:

| Row | Source channel | Pi channel (config.example.yaml) |
|-----|----------------|----------------------------------|
| Ail | 1 | roll |
| Ele | 2 | pitch |
| Thr | 3 | throttle |
| Rud | 4 | yaw |

- **Mode**: start with **Replace** (the Pi's value replaces the stick). Use **Add** only if you
  want the Pocket's own sticks to trim the Pi's input.
- **Weight**: 100%; a negative value reverses a control.
- Keep the Pocket's trims centred, per the manual.
- Aux channels (arm switch etc.): student channels 5-8 are not covered by the four rows; map
  them with Special function **Trainer** value **Chans** (all channels) or read them in mixes.
  How exactly channel 5+ reaches a mix is not confirmed by the pages read; check on the radio.

## 3. The kill switch

Special Functions > new line > switch = a physical switch of your choice > function **Trainer** >
Value **Axis** (all primary controls; options: Axis, Rud, Ele, Thr, Ail, Chans).

Trainer passthrough is only active while that switch is on. Switch off = the Pocket's own sticks
fly the model again. This is the manual override; keep it within reach of a finger at all times.

The virtual switch **Tnr** is ON while the trainer link is active. It can drive a special
function or a curve, e.g. an audible warning when the link drops. Not tested.

## 4. Open: behaviour on signal loss

The manual pages read do not describe what happens when the PPM signal stops. Test with props
off and no battery: start the Pi, then kill the Pi process and watch the channel monitor.
Record the result in this file before any real flight.
