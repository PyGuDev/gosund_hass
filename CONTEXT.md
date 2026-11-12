# Gosund EP8 Local Control

Локальное управление умной розеткой EP8 из Home Assistant без облака GHome/Tuya.

## Language

**EP8**:
Конкретная умная розетка Gosund в локальной сети, уже привязанная к аккаунту GHome. В Device Registry Home Assistant отображается как «Gosund EP8».
_Avoid_: plug, outlet, device (как имя продукта)

**Relay**:
Главный силовой выход EP8; в Home Assistant представляется сущностью `switch`.
_Avoid_: реле DPS, power button, outlet state

**Integration**:
Собственный Home Assistant domain `gosund_ep8` (`custom_component`), обслуживающий только эту EP8 и ставящийся как HACS custom repository.
_Avoid_: LocalTuya-конфиг, addon, MQTT bridge (как замена этой Integration)

**Config Entry**:
Сохранённая в Home Assistant конфигурация одного экземпляра Integration (host, device id, Local Key, интервал опроса).
_Avoid_: secrets file, `.env`, configuration.yaml (как основной способ настройки)

**Local Key**:
Секрет протокола Tuya LAN 3.3 для расшифровки и подписи локальных команд EP8.
_Avoid_: password, token, API key

**DPS 1**:
Булева точка данных протокола, соответствующая Relay (`true` = включено, `false` = выключено).
_Avoid_: switch id, channel 1 (без уточнения, что это DPS)

**LAN Client**:
Минимальный локальный клиент Tuya LAN 3.3 внутри Integration (query/control DPS 1), без зависимости tinytuya.
_Avoid_: tinytuya, LocalTuya, cloud API

**Polling**:
Периодический локальный опрос состояния Relay; по умолчанию каждые 30 секунд, плюс обновление после своих команд.
_Avoid_: push, MQTT state, cloud status

**Direct LAN Session**:
Кратковременное TCP-подключение Home Assistant напрямую к EP8 на порту 6668 для одной операции (query или control), без облака и посредников.
_Avoid_: persistent session (как обязательная модель), cloud relay, phone bridge
