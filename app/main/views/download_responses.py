# coding: utf-8
from __future__ import unicode_literals
import inflection

from flask import abort
from flask_login import current_user

from app import data_api_client
from .buyers import CLOSED_PUBLISHED_BRIEF_STATUSES
from .. import main, content_loader
from ..helpers.buyers_helpers import get_framework_and_lot, get_sorted_responses_for_brief, is_brief_correct_debug

from dmutils.views import DownloadFileView


class DownloadBriefResponsesView(DownloadFileView):
    """
    Generate a spreadsheet with the responses to an opportunity

    This view allows a buyer to download all the responses to their opportunity
    as a spreadsheet (ODS), so they can mark the responses offline.

    If the opportunity was on DOS1 this view will generate a CSV, at some
    point it would be nice to remove the CSV code, however currently users can
    still download their old responses.
    """

    def get_responses(self, brief):
        return get_sorted_responses_for_brief(brief, self.data_api_client)

    def _init_hook(self, **kwargs):
        self.data_api_client = data_api_client
        self.content_loader = content_loader

    def determine_filetype(self, file_context=None, **kwargs):
        responses = file_context['responses']

        # CSV if DOS1, ODS otherwise
        if responses and 'essentialRequirementsMet' in responses[0]:
            return DownloadFileView.FILETYPES.ODS

        return DownloadFileView.FILETYPES.CSV

    def get_file_context(self, **kwargs):
        get_framework_and_lot(
            kwargs['framework_slug'],
            kwargs['lot_slug'],
            self.data_api_client,
            allowed_statuses=['live', 'expired'],
            must_allow_brief=True,
        )

        brief = self.data_api_client.get_brief(kwargs['brief_id'])["briefs"]

        if not is_brief_correct_debug(brief, kwargs['framework_slug'],
                                      kwargs['lot_slug'], current_user.id):
            abort(404)

        if brief['status'] not in CLOSED_PUBLISHED_BRIEF_STATUSES:
            abort(404)

        file_context = {
            'brief': brief,
            'responses': self.get_responses(brief),
            'filename': 'supplier-responses-{0}'.format(inflection.parameterize(str(brief['title']))),
        }

        return file_context

    def get_questions(self, framework_slug, lot_slug, manifest):
        section = 'view-response-to-requirements'
        result = self.content_loader.get_manifest(framework_slug, manifest)\
                                    .filter({'lot': lot_slug}, dynamic=False)\
                                    .get_section(section)

        return result.questions if result else []

    def generate_csv_rows(self, file_context):
        # This method works for DOS1 only

        column_headings = []
        question_key_sequence = []
        boolean_list_questions = []
        csv_rows = []
        brief, responses = file_context['brief'], file_context['responses']

        questions = self.get_questions(brief['frameworkSlug'],
                                       brief['lotSlug'],
                                       'legacy_output_brief_response')

        # Build header row from manifest and add it to the list of rows
        for question in questions:
            question_key_sequence.append(question.id)
            if question['type'] == 'boolean_list' and brief.get(question.id):
                column_headings.extend(brief[question.id])
                boolean_list_questions.append(question.id)
            else:
                column_headings.append(question.name)
        csv_rows.append(column_headings)

        # Add a row for each eligible response received
        for brief_response in responses:
            if all(brief_response['essentialRequirements']):
                row = []
                for key in question_key_sequence:
                    if key in boolean_list_questions:
                        row.extend(brief_response.get(key))
                    else:
                        row.append(brief_response.get(key))
                csv_rows.append(row)

        return csv_rows

    def populate_styled_ods_with_data(self, spreadsheet, file_context):
        sheet = spreadsheet.sheet("Supplier evidence")

        brief, responses = file_context['brief'], file_context['responses']
        questions = self.get_questions(brief['frameworkSlug'],
                                       brief['lotSlug'],
                                       'output_brief_response')

        # two intro columns for boolean and dynamic lists
        sheet.create_column(stylename="col-wide", defaultcellstylename="cell-default")
        sheet.create_column(stylename="col-wide", defaultcellstylename="cell-default")

        # HEADER
        row = sheet.create_row("header", stylename="row-tall")
        row.write_cell(brief['title'], stylename="cell-header", numbercolumnsspanned=str(len(responses) + 2))

        # QUESTIONS
        for question in questions:
            if question._data['type'] in ('boolean_list', 'dynamic_list'):
                length = len(brief[question.id])

                for i, requirement in enumerate(brief[question.id]):
                    row = sheet.create_row("{0}[{1}]".format(question.id, i))
                    if i == 0:
                        row.write_cell(question.name, stylename="cell-header", numberrowsspanned=str(length))
                    else:
                        row.write_covered_cell()
                    row.write_cell(requirement, stylename="cell-default")
            else:
                row = sheet.create_row(question.id, stylename="row-tall-optimal")
                row.write_cell(question.name, stylename="cell-header", numbercolumnsspanned="2")
                row.write_covered_cell()

        # RESPONSES
        for response in responses:
            sheet.create_column(stylename="col-extra-wide", defaultcellstylename="cell-default")

            for question in questions:
                if question._data['type'] == 'dynamic_list':
                    if not brief.get(question.id):
                        continue

                    for i, item in enumerate(response[question.id]):
                        row = sheet.get_row("{0}[{1}]".format(question.id, i))
                        # TODO this is stupid, fix it (key should not be hard coded)
                        row.write_cell(item.get('evidence') or '', stylename="cell-default")

                elif question.type == 'boolean_list' and brief.get(question.id):
                    if not brief.get(question.id):
                        continue

                    for i, item in enumerate(response[question.id]):
                        row = sheet.get_row("{0}[{1}]".format(question.id, i))
                        row.write_cell(str(bool(item)).lower(), stylename="cell-default")

                else:
                    sheet.get_row(question.id).write_cell(response.get(question.id, ''), stylename="cell-default")

        return spreadsheet


main.add_url_rule('/frameworks/<framework_slug>/requirements/<lot_slug>/<brief_id>/responses/download',
                  view_func=DownloadBriefResponsesView.as_view(str('download_brief_responses')),
                  methods=['GET'])
