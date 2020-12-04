init_services: SERVICES_COMPOSE_PATH = docker/docker-compose.yaml
init_services:
	@docker-compose --env-file docker/docker-compose.env -f $(SERVICES_COMPOSE_PATH) up -d

clean_services: SERVICES_COMPOSE_PATH = docker/docker-compose.yaml
clean_services:
	@docker-compose --env-file docker/docker-compose.env -f $(SERVICES_COMPOSE_PATH) down

shell:
	@./docker/run.sh built_shell

build_container:
	./docker/build.sh container
