# Copyright 2021-2023 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from .http import ExportDownloadResource, ExportResource
from .services import ExportService


class Plugin:
    def load(self, dependencies):
        api = dependencies['api']
        dao = dependencies['dao']

        export_service = ExportService(dao)

        api.add_resource(
            ExportResource,
            '/exports/<uuid:export_uuid>',
            resource_class_args=[export_service],
            endpoint='export_resource',
        )

        api.add_resource(
            ExportDownloadResource,
            '/exports/<uuid:export_uuid>/download',
            resource_class_args=[export_service],
            endpoint='export_download_resource',
        )
