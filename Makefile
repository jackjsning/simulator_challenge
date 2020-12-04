redis: SERVICES_COMPOSE_PATH = docker/docker-compose.yaml
redis:
	@docker-compose --env-file docker/docker-compose.env -f $(SERVICES_COMPOSE_PATH) up -d

clean_redis: SERVICES_COMPOSE_PATH = docker/docker-compose.yaml
clean_redis:
	@docker-compose --env-file docker/docker-compose.env -f $(SERVICES_COMPOSE_PATH) down

shell:
	@./docker/run.sh built_shell

format:
	@./docker/run.sh built black /built/src

build_container:
	./docker/build.sh container
