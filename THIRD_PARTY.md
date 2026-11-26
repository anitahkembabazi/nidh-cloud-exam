# Third-party material used in Milestone 3

## Python packages

These are the direct and transitive packages pinned in `requirements.txt`. Each row cites the release metadata and the text of its declared license.

| Package pin | Source | License |
| --- | --- | --- |
| `annotated-doc==0.0.7` | [PyPI release](https://pypi.org/project/annotated-doc/0.0.7/) | [MIT](https://spdx.org/licenses/MIT.html) |
| `annotated-types==0.8.0` | [PyPI release](https://pypi.org/project/annotated-types/0.8.0/) | [MIT](https://spdx.org/licenses/MIT.html) |
| `anyio==4.16.0` | [PyPI release](https://pypi.org/project/anyio/4.16.0/) | [MIT](https://spdx.org/licenses/MIT.html) |
| `click==8.5.1` | [PyPI release](https://pypi.org/project/click/8.5.1/) | [BSD-3-Clause](https://spdx.org/licenses/BSD-3-Clause.html) |
| `fastapi==0.165.0` | [PyPI release](https://pypi.org/project/fastapi/0.165.0/) | [MIT](https://spdx.org/licenses/MIT.html) |
| `h11==0.16.0` | [PyPI release](https://pypi.org/project/h11/0.16.0/) | [MIT](https://spdx.org/licenses/MIT.html) |
| `idna==3.20` | [PyPI release](https://pypi.org/project/idna/3.20/) | [BSD-3-Clause](https://spdx.org/licenses/BSD-3-Clause.html) |
| `opentelemetry-api==1.45.2` | [PyPI release](https://pypi.org/project/opentelemetry-api/1.45.2/) | [Apache-2.0](https://spdx.org/licenses/Apache-2.0.html) |
| `pika==1.3.2` | [PyPI release](https://pypi.org/project/pika/1.3.2/) | [BSD-3-Clause](https://spdx.org/licenses/BSD-3-Clause.html) |
| `psycopg==3.3.9` | [PyPI release](https://pypi.org/project/psycopg/3.3.9/) | [LGPL-3.0-only](https://spdx.org/licenses/LGPL-3.0-only.html) |
| `psycopg-binary==3.3.9` | [PyPI release](https://pypi.org/project/psycopg-binary/3.3.9/) | [LGPL-3.0-only](https://spdx.org/licenses/LGPL-3.0-only.html) |
| `pydantic==2.14.4` | [PyPI release](https://pypi.org/project/pydantic/2.14.4/) | [MIT](https://spdx.org/licenses/MIT.html) |
| `pydantic_core==2.50.5` | [PyPI release](https://pypi.org/project/pydantic_core/2.50.5/) | [MIT](https://spdx.org/licenses/MIT.html) |
| `starlette==1.10.0` | [PyPI release](https://pypi.org/project/starlette/1.10.0/) | [BSD-3-Clause](https://spdx.org/licenses/BSD-3-Clause.html) |
| `typing-inspection==0.4.5` | [PyPI release](https://pypi.org/project/typing-inspection/0.4.5/) | [MIT](https://spdx.org/licenses/MIT.html) |
| `typing_extensions==4.16.0` | [PyPI release](https://pypi.org/project/typing_extensions/4.16.0/) | [PSF-2.0](https://spdx.org/licenses/PSF-2.0.html) |
| `tzdata==2026.6` | [PyPI release](https://pypi.org/project/tzdata/2026.6/) | [Apache-2.0](https://spdx.org/licenses/Apache-2.0.html) |
| `uvicorn==0.54.0` | [PyPI release](https://pypi.org/project/uvicorn/0.54.0/) | [BSD-3-Clause](https://spdx.org/licenses/BSD-3-Clause.html) |

The Psycopg binary wheel also bundles native libraries, including PostgreSQL’s libpq. Bundled components retain their own licenses. The tzdata package distributes the IANA time zone database. [Psycopg installation notes](https://www.psycopg.org/psycopg3/docs/basic/install.html#binary-installation) · [IANA database notices](https://data.iana.org/time-zones/tzdb/LICENSE)

## Docker images

The Compose files reference the following tags. The RabbitMQ bootstrap service reuses the broker image. The image references use tags without digests. Image layers and bundled software retain their respective licenses.

| Image reference | Use in M3 | Source and licensing |
| --- | --- | --- |
| `rabbitmq:4-alpine` | Three brokers host replicated queues. The tag selects the RabbitMQ 4 Alpine variant and can move between builds. | [Official image](https://hub.docker.com/_/rabbitmq). RabbitMQ server and core plugins use MPL-2.0, with exceptions documented in the [upstream license notice](https://github.com/rabbitmq/rabbitmq-server/blob/main/LICENSE). The [image build scripts](https://github.com/docker-library/rabbitmq/blob/master/LICENSE) use MIT. |
| `cockroachdb/cockroach:v25.4.21` | Three database nodes store vaccination, sensor and audit records. | [Publisher’s image](https://hub.docker.com/r/cockroachdb/cockroach). The [CockroachDB Software License for v25.4.21](https://github.com/cockroachdb/cockroach/blob/v25.4.21/LICENSE) defines the terms for limited non-production use and license keys. |

## Configuration and templates

The launcher uses Docker Compose to read `compose.yaml` and `compose.override.yaml`. The files identify their upstream images. The available project records do not identify an external template or snippet author. Before approval, the student should add the source, license and affected file for any code or configuration they copied or adapted. [Docker Compose source and license](https://github.com/docker/compose/blob/main/LICENSE)
