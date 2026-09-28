from src.config import Config, KafkaConfig, ServerConfig, ValkeyConfig


class TestConfig:
    def test_default_kafka_config(self):
        config = KafkaConfig()
        assert config.brokers == "localhost:9092"
        assert config.client_queue_size == 100

    def test_kafka_broker_list(self):
        config = KafkaConfig(brokers="broker1:9092,broker2:9092,broker3:9092")
        assert config.client_queue_size == 100
        brokers = config.brokers
        broker_list = [b.strip() for b in brokers.split(",") if b.strip()]
        assert broker_list == ["broker1:9092", "broker2:9092", "broker3:9092"]

    def test_default_server_config(self):
        config = ServerConfig()
        assert config.host == "0.0.0.0"
        assert config.port == 8888

    def test_default_valkey_config(self):
        config = ValkeyConfig()
        assert config.host == "localhost"
        assert config.port == 6379

    def test_full_config(self):
        config = Config()
        assert config.kafka.brokers == "localhost:9092"
        assert config.server.host == "0.0.0.0"
        assert config.server.port == 8888

    def test_kafka_broker_list_single(self):
        config = KafkaConfig(brokers="localhost:9092")
        broker_list = [b.strip() for b in config.brokers.split(",") if b.strip()]
        assert broker_list == ["localhost:9092"]

    def test_kafka_broker_list_property(self):
        config = Config()
        assert config.kafka_broker_list == ["localhost:9092"]