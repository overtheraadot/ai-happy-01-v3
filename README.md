# ai-happy-01 — a giggling puppy in a sunny meadow

make.fun competition **ai-happy-01** ("Make the AI judge happy", $250).
This entry is a program that draws one image: a golden retriever puppy
giggling in a sunny wildflower meadow while a bright orange butterfly
rests on its nose.

## The scene

A low golden sun with rays in the upper left, puffy clouds, rolling
green hills with a few little trees, and a meadow full of daisies,
tulips and lavender. Front and centre, the puppy: floppy ears, eyes
squeezed shut with joy, rosy cheeks, tongue out in a happy grin — and
the orange butterfly on its nose, wings half-folded. Four more
butterflies drift through the air, and pollen sparkles in the light.

## How to run

Python 3.13, standard library only — nothing to install.

```sh
python3 main.py
```

The program writes `entry.png` (1024x1024 PNG, well under 1 MiB).
Output location, in order:

1. `$MAKEFUN_OUTPUT_DIR` when set,
2. `/output/entry.png` when a directory `/output` exists (this is the
   path the make.fun grader uses: it runs as an unprivileged user on a
   read-only filesystem with a writable `/output` mounted),
3. `./entry.png` otherwise.

## Determinism

The scene is fully deterministic: a fixed seed, no timestamps, no
network, no files read. Run it twice and the two PNGs are byte-identical
(sha256 `4fecd1eadfbf317fba4db2b8d1093888f6277c02f624e8af101f7fda8b352f5c`,
43,595 bytes, ~0.5 s per run).

## License

MIT — see [LICENSE](LICENSE).
