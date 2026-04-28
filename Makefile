# K.516f Prototype — build orchestration
#
# Usage:
#   make all       # regenerate every artefact
#   make midi      # MIDI files only
#   make audio     # WAV files only
#   make entropy   # entropy validation log
#   make clean     # remove outputs/

PY      := python3
SRC     := src
OUT     := outputs

.PHONY: all midi audio entropy clean help

help:
	@echo "make all      — regenerate all artefacts"
	@echo "make midi     — MIDI generation"
	@echo "make audio    — WAV synthesis"
	@echo "make entropy  — entropy validation"
	@echo "make clean    — remove outputs/"

all: midi audio entropy

midi: $(OUT)/k516f_triangular_seed42.mid \
      $(OUT)/k516f_uniform_seed42.mid

$(OUT)/k516f_triangular_seed42.mid:
	$(PY) $(SRC)/generator.py --dist triangular --seed 42 --out $@

$(OUT)/k516f_uniform_seed42.mid:
	$(PY) $(SRC)/generator.py --dist uniform --seed 42 --out $@

audio: $(OUT)/k516f_triangular_seed42.wav

$(OUT)/k516f_triangular_seed42.wav:
	$(PY) $(SRC)/synth.py --dist triangular --seed 42 --out $@

entropy: $(OUT)/entropy_validation.json

$(OUT)/entropy_validation.json:
	$(PY) $(SRC)/entropy_validation.py \
	    --out-json $(OUT)/entropy_validation.json \
	    --out-txt  $(OUT)/entropy_validation.txt

clean:
	rm -rf $(OUT)/*.mid $(OUT)/*.wav $(OUT)/entropy_validation.*
