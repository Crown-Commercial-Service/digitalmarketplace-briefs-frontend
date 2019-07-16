# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from app import data_api_client
from flask import current_app

from dmutils.flask import timed_render_template as render_template

from .. import dos
from ..helpers.buyers_helpers import get_framework_and_lot


@dos.route('/frameworks/<framework_slug>/requirements/user-research-studios', methods=['GET'])
def studios_start_page(framework_slug):
    # Check framework is live and has the user-research-studios lot
    framework, lot = get_framework_and_lot(
        framework_slug, 'user-research-studios', data_api_client, allowed_statuses=['live']
    )

    return render_template(
        "buyers/studios_start_page.html",
        framework=framework,
        support_email_address=current_app.config['SUPPORT_EMAIL_ADDRESS']
    ), 200


@dos.route('/frameworks/<framework_slug>/requirements/<lot_slug>', methods=['GET'])
def info_page_for_starting_a_brief(framework_slug, lot_slug):
    framework, lot = get_framework_and_lot(framework_slug, lot_slug, data_api_client,
                                           allowed_statuses=['live'], must_allow_brief=True)
    return render_template(
        "buyers/start_brief_info.html",
        framework=framework,
        lot=lot
    ), 200
