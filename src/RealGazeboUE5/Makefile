# RealGazeboUE5 — Unreal Engine 5 photorealistic rendering integration
#
# This directory will contain the UE5 project as a git submodule.
# For now, it provides a standalone UDP receiver that can be used
# to verify the data flow from libRealGazebo.so without UE5.
#
# Called from root Makefile via: make -C src/RealGazeboUE5 <target>

UE5_RECEIVER = ue5_receiver

$(UE5_RECEIVER): ue5_receiver.cpp
	g++ -std=c++17 -o $(UE5_RECEIVER) ue5_receiver.cpp

ue5-mock: $(UE5_RECEIVER)    ## Listen to UDP from libRealGazebo.so (port 5005)
	@echo "=== RealGazebo UDP Receiver ==="
	@echo "  Listening on port 5005. Start simulation to see vehicle poses."
	@./$(UE5_RECEIVER) 5005

clean:
	rm -f $(UE5_RECEIVER)

.PHONY: ue5-mock clean
