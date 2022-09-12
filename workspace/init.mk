#!/bin/bash


init:
	cd $(NOOP_HOME); \
	if [  -d "single-build" ]; then \
		rm -r single-build; \
	fi
	cd $(NOOP_HOME); \
	if [  -d "dual-build" ]; then \
		rm -r dual-build; \
	fi
	cd $(NOOP_HOME);proxychains make init
	cd $(NOOP_HOME);make emu EMU_THREADS=8 EMU_TRACE=1 -j
	cd $(NOOP_HOME);mv build single-build
	cd $(NOOP_HOME);make emu EMU_THREADS=8 EMU_TRACE=1 NUM_CORES=2 -j
	cd $(NOOP_HOME);mv build dual-build


test:
	echo test!