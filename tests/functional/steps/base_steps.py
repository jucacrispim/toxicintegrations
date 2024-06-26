# -*- coding: utf-8 -*-
# Copyright 2024 Juca Crispim <juca@poraodojuca.dev>

# This file is part of toxicintegrations.

# toxicintegrations is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# toxicintegrations is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with toxicintegrations. If not, see <http://www.gnu.org/licenses/>.

from selenium.webdriver.common.by import By
from toxicintegrations import settings
from toxicwebui import settings as ui_settings
from behave import given, when


@when('he goes to the repository settings interface')
def go_repo_settings_page(context):
    browser = context.browser
    browser.get(settings.TOXICUI_URL + 'settings/repositories')


@given('the user is logged in the web interface')
def logged_in_webui(context):
    browser = context.browser
    base_url = 'http://{}:{}/'.format(ui_settings.TEST_WEB_HOST,
                                      ui_settings.TORNADO_PORT)
    url = base_url + 'login'
    browser.get(url)

    if not browser.is_logged:
        browser.do_login(url, 'someguy', '123')

    def fn():
        try:
            el = browser.find_element(By.CLASS_NAME, 'logout-link-container')
            el = el if el and el.is_displayed() else None
        except IndexError:
            el = None

        return el

    el = browser.wait_element_become_present(fn)

    browser.wait_element_become_visible(el)
