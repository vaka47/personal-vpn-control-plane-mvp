.PHONY: test demo server-config profile-apple profile-android profile-windows clean-demo

test:
	python3 -m unittest discover -s tests

demo:
	./scripts/demo.sh

server-config:
	python3 -m vpn_control_plane.cli render-server-config \
		--customer-id demo-customer \
		--server-fqdn vpn-demo.example.com \
		--output dist/server/swanctl.conf

profile-apple:
	python3 -m vpn_control_plane.cli generate-profile \
		--customer-id demo-customer \
		--slot 1 \
		--platform apple \
		--server-fqdn vpn-demo.example.com \
		--device-name "Demo iPhone"

profile-android:
	python3 -m vpn_control_plane.cli generate-profile \
		--customer-id demo-customer \
		--slot 2 \
		--platform android \
		--server-fqdn vpn-demo.example.com \
		--device-name "Demo Android"

profile-windows:
	python3 -m vpn_control_plane.cli generate-profile \
		--customer-id demo-customer \
		--slot 3 \
		--platform windows \
		--server-fqdn vpn-demo.example.com \
		--device-name "Demo Windows"

clean-demo:
	rm -rf data dist

