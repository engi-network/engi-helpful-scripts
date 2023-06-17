from yaml import load, dump
try:
    from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:
    from yaml import Loader, Dumper

def get_docker_compose_test_service_cmd(compose_path):
    with open(compose_path, 'r') as compose_file:
        docker_compose_config = load(compose_file, Loader=Loader)
        return docker_compose_config['x-test-framework']
