# RealGazeboUE5 — Unreal Engine 5 photorealistic rendering integration
#
# The official UE5 binary is distributed by SUV Lab as a pre-built download.
# Two options:
#   1. Download the pre-built binary (recommended, ~2GB)
#   2. Use the standalone UDP mock receiver (debugging/verification)
#
# Called from root Makefile via: make -C src/RealGazeboUE5 <target>

UE5_RECEIVER = ue5_receiver
UE5_DIR = project
UE5_URL_BASE = https://realgazebo.cbnu.ac.kr/download/v1.2
ZIP_FILE = Linux_RealGazebo_CTrack.zip

$(UE5_RECEIVER): ue5_receiver.cpp
	g++ -std=c++17 -o $(UE5_RECEIVER) ue5_receiver.cpp

ue5-mock: $(UE5_RECEIVER)    ## Listen to UDP from libRealGazebo.so (port 5005)
	@echo "=== RealGazebo UDP Receiver ==="
	@echo "  Listening on port 5005."
	@./$(UE5_RECEIVER) 5005

download:               ## Download the official UE5 binary (~2GB zip) with progress bar
	@echo "=== Downloading RealGazebo UE5 binary ==="
	@echo "  From: $(UE5_URL_BASE)/$(ZIP_FILE)"
	@echo "  To:   $$(pwd)/$(UE5_DIR)/$(ZIP_FILE)"
	@echo ""
	@mkdir -p $(UE5_DIR)
	@echo "  Press Ctrl+C to cancel download."
	@echo ""
	@curl -L "$(UE5_URL_BASE)/$(ZIP_FILE)" -o $(UE5_DIR)/$(ZIP_FILE)

check-download:         ## Show file size so far
	@ls -lh $(UE5_DIR)/$(ZIP_FILE) 2>/dev/null || echo "File not found"

extract:                ## Extract downloaded zip
	@echo "=== Extracting ==="
	@cd $(UE5_DIR) && unzip -q $(ZIP_FILE) && echo "  Extracted. Run: make -C src/RealGazeboUE5 run"

run:                    ## Run the official UE5 binary (needs download first)
	@echo "=== Starting RealGazebo UE5 ==="
	@UE5_EXE=$$(find $(UE5_DIR) -name "*.sh" -o -name "*.exe" 2>/dev/null | head -1); \
	if [ -z "$$UE5_EXE" ]; then \
	  echo "  UE5 binary not found. Run 'make download' first."; \
	  exit 1; \
	fi; \
	echo "  Running: $$UE5_EXE"; \
	chmod +x "$$UE5_EXE"; \
	exec "$$UE5_EXE"

clean:
	rm -f $(UE5_RECEIVER)
	rm -rf $(UE5_DIR)

.PHONY: ue5-mock download run clean
