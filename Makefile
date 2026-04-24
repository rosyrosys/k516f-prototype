# Makefile — K.516f prototype
# Reproduces all archived artefacts from source in one command.
#
#   make            same as `make all`
#   make all        regenerate MIDI + WAV + entropy validation
#   make midi       only the three MIDI files
#   make wav        only the three WAV files
#   make validate   only the Monte-Carlo entropy cross-check
#   make clean      remove generated artefacts (keeps the folder)

PYTHON ?= python3
OUT := outputs

.PHONY: all midi wav validate clean

all: midi wav validate

midi:
	$(PYTHON) src/generator.py --dist triangular --seed 42   --out $(OUT)/k516f_triangular_seed42.mid
	$(PYTHON) src/generator.py --dist uniform    --seed 42   --out $(OUT)/k516f_uniform_seed42.mid
	$(PYTHON) src/generator.py --dist triangular --seed 1792 --out $(OUT)/k516f_triangular_seed1792.mid

wav:
	$(PYTHON) src/synth.py --dist triangular --seed 42   --out $(OUT)/k516f_triangular_seed42.wav
	$(PYTHON) src/synth.py --dist uniform    --seed 42   --out $(OUT)/k516f_uniform_seed42.wav
	$(PYTHON) src/synth.py --dist triangular --seed 1792 --out $(OUT)/k516f_triangular_seed1792.wav

validate:
	$(PYTHON) src/entropy_validation.py

clean:
	- rm $(OUT)/*.mid $(OUT)/*.wav $(OUT)/*.json $(OUT)/*.txt 2>/dev/null
