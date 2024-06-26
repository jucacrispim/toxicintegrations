# -*- coding: utf-8 -*-
# package with behave tests

import os
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import (
    NoSuchElementException,
    StaleElementReferenceException
)
from selenium.webdriver.common.action_chains import ActionChains
import undetected_chromedriver as uc
from toxiccore.utils import now, datetime2string


class SeleniumBrowserException(Exception):
    pass


class SeleniumBrowser(uc.Chrome):

    def __init__(self, *args, **kwargs):
        options = webdriver.ChromeOptions()
        options.add_argument('--start-maximized')
        options.add_argument('--no-sandbox')
        options.add_experimental_option(
            "excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--disable-dev-shm-usage')
        kwargs['version_main'] = int(os.environ.get('CHROME_VERSION', 102))
        super().__init__(*args, chrome_options=options, **kwargs)
        # self.maximize_window()
        self.implicitly_wait(10)

    def click(self, element):
        """Clicks in a element using ActionChains.

        :param element: Um elemento para clicar."""

        action = ActionChains(self).click(element)
        action.perform()

    def _get_screenshot_filename(self):
        ts = str(int(time.time()))
        dt = datetime2string(now(), dtformat='%Y/%m/%d')
        fname = '{}.png'.format(ts)
        return dt, fname

    def save_screenshot(self):
        path, fname = self._get_screenshot_filename()
        path = os.path.join('artifacts', path)
        os.makedirs(path, exist_ok=True)
        self.get_screenshot_as_file(os.path.join(path, fname))

    def wait_text_become_present(self, text, timeout=30):
        """Waits until a text is present in the page source.

        :param text: The text that should be present in the page.
        :param timeout: timeout in seconds for the operation."""

        r = int(timeout * 10)

        for index in range(r):
            time.sleep(0.1)
            if text in self.page_source:
                return True

        raise SeleniumBrowserException(
            'text %s not present after %s seconds' % (text, timeout))

    def wait_text_vanishes(self, text, timeout=30):
        """Waits until a text is not present anyomore in the page source.

        :param text: The text that should be present in the page.
        :param timeout: timeout in seconds for the operation."""

        r = int(timeout * 10)

        for index in range(r):
            time.sleep(0.1)
            if text not in self.page_source:
                return True

        raise SeleniumBrowserException(
            'text %s did not vanish after %s seconds' % (text, timeout))

    def do_login(self, url, username, passwd):
        """Do login in the web interface.

        :param url: Login page url.
        :param username: Username for login.
        :param passwd: Password for login."""

        self.get(url)
        username_input = self.find_element(By.ID, 'inputUsername')
        username_input.send_keys(username)

        passwd_input = self.find_element(By.ID, 'inputPassword')
        passwd_input.send_keys(passwd)
        btn = self.find_element(By.ID, 'btn-login')
        self.click(btn)

    def click_link(self, link_text):
        """Clicks in  link indicated by link_text"""

        self.click(self.find_element(By.PARTIAL_LINK_TEXT, link_text))

    @property
    def is_logged(self):
        """True if the browser is already logged in the web interface."""

        try:
            self.implicitly_wait(0)
            self.find_element(By.ID, 'inputPassword')
            is_logged = False
        except NoSuchElementException:
            is_logged = True
        finally:
            self.implicitly_wait(10)

        return is_logged

    def wait_element_become_visible(self, el, timeout=10):
        """Waits until an element become visible.

        :param el: A page element
        :param timeout: Timeout for the operation."""

        r = int(timeout * 10)

        for index in range(r):
            time.sleep(0.1)
            if el.is_displayed():
                return True

        raise SeleniumBrowserException(
            'The element %s not visible after %s seconds' % (el, timeout))

    def wait_element_become_hidden(self, el, timeout=10):
        """Waits until an element become hidden.

        :param el: A page element
        :param timeout: Timeout for the operation."""

        r = int(timeout * 10)

        for index in range(r):
            time.sleep(0.1)
            if not el.is_displayed():
                return True

        raise SeleniumBrowserException(
            'The element %s not hidden after %s seconds' % (el, timeout))

    def wait_element_become_present(self, fn, timeout=10, check_display=True):
        """Waits until an element is present in the DOM.

        :param fn: A function that should return an element. If no return value
          tries again until timeout is reached.
        :param timeout: Timeout for the operation.
        :param check_display: Checks if the element is displayed before
          returning it.
        """

        r = int(timeout * 10)

        for index in range(r):
            time.sleep(0.1)
            try:
                el = fn()
                if check_display:
                    el = el if el.is_displayed() else None
            except Exception:
                el = None

            if el:
                return el

    def wait_element_be_removed(self, fn, timeout=10):
        """Waits until an element is not present in the DOM anymore.

        :param fn: A function that should return an element. If return value
          is true, tries again until timeout is reached.
        :param timeout: Timeout for the operation."""

        r = int(timeout * 10)

        for index in range(r):
            time.sleep(0.1)
            try:
                el = fn()
            except Exception:
                el = True

            if not el:
                return el

    def refresh_until(self, fn, timeout=10):
        """Reloads a page until ``fn`` returns True.

        :param fn: A callable which returns a boolean.
        :param timeout: Timeout for the operation."""

        for index in range(timeout):
            self.refresh()
            time.sleep(1)
            try:
                r = fn()
            except Exception:
                r = False

            if r:
                return r

    def click_and_retry_on_stale(self, fn, retry=True):
        """Clicks in an element and it again in case of
        StaleElementReferenceException error.
        """

        el = self.wait_element_become_present(fn)
        try:
            el.click()
        except StaleElementReferenceException:
            el = self.click_and_retry_on_stale(fn, retry=False)

        return el


def take_screenshot(fn):

    def wrapper(context, *args, **kwargs):
        try:
            r = fn(context, *args, **kwargs)
        except Exception as e:
            browser = context.browser
            browser.save_screenshot()
            raise e

        return r

    return wrapper
