# -*- coding: utf-8 -*-
# Copyright 2018, 2024 Juca Crispim <juca@poraodojuca.net>

# This file is part of toxicbuild.

# toxicbuild is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# toxicbuild is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.

# You should have received a copy of the GNU Affero General Public License
# along with toxicbuild. If not, see <http://www.gnu.org/licenses/>.

from behave import given, when, then
from selenium.webdriver.common.by import By

from toxicintegrations import settings


@when('he inserts "{user_name}" as user name')
def user_inserts_username_login(context, user_name):
    browser = context.browser
    username_input = browser.find_element(By.ID, 'inputUsername')
    username_input.send_keys(user_name)


@when('inserts "{passwd}" as password')
def user_inserts_password_login(context, passwd):
    browser = context.browser
    passwd_input = browser.find_element(By.ID, 'inputPassword')
    passwd_input.send_keys(passwd)


@when('clicks in the login button')
def user_clicks_login_button(context):
    browser = context.browser
    btn = browser.find_element(By.ID, 'btn-login')
    btn.click()


@then('he sees the main page')
def user_sees_main_main_page_login(context):
    browser = context.browser
    txt = 'Logout'
    is_present = browser.wait_text_become_present(txt)
    assert is_present


@given('the user is sent to the setup url by github')
def user_redirected_from_githbu(context):
    # Here we assume github redirected us correctly and
    # we simply access the setup page.
    browser = context.browser
    browser.get(settings.GITHUB_SETUP_URL)


@when('he is redirected to the login page')
def user_redirected_to_main_page(context):
    browser = context.browser
    login = browser.find_element_by_class_name('login-container')
    assert login


@then('his repositories beeing imported from github')
def user_sees_repositories_imported(context):
    browser = context.browser

    def fn():
        repo_row = browser.wait_text_become_present('toxic-ghintegration-test',
                                                    timeout=1)
        return bool(repo_row)

    r = browser.refresh_until(fn)
    assert r
