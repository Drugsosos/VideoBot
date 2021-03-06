from pyppeteer import launch
from pyppeteer.page import Page as PageCls
from pyppeteer.element_handle import ElementHandle as ElementHandleCls
from pyppeteer.browser import Browser as BrowserCls
from pyppeteer.errors import TimeoutError as BrowserTimeoutError

from os import getenv
from attr import attrs, attrib
from attr.validators import instance_of

from src.common import str_to_bool

from typing import TypeVar, Optional, Callable, Union

_function = TypeVar('_function', bound=Callable[..., object])
_exceptions = TypeVar('_exceptions', bound=Optional[Union[type, tuple, list]])


@attrs
class ExceptionDecorator:
    # TODO add typing
    __exception: Optional[_exceptions] = attrib(default=None)
    __default_exception: _exceptions = attrib(default=BrowserTimeoutError)

    def __attrs_post_init__(self):
        if not self.__exception:
            self.__exception = self.__default_exception

    def __call__(
            self,
            func: _function,
    ):
        async def wrapper(*args, **kwargs):
            try:
                obj_to_return = await func(*args, **kwargs)
                return obj_to_return
            except Exception as caughtException:
                import logging

                if isinstance(self.__exception, type):
                    if not type(caughtException) == self.__exception:
                        logging.basicConfig(filename='.webdriver.log', filemode='w', encoding='utf-8',
                                            level=logging.DEBUG)
                        logging.error(f'unexpected error - {caughtException}')
                else:
                    if not type(caughtException) in self.__exception:
                        logging.error(f'unexpected error - {caughtException}')

        return wrapper


def catch_exception(
        func: Optional[_function],
        exception: Optional[_exceptions] = None,
) -> ExceptionDecorator | _function:
    exceptor = ExceptionDecorator(exception)
    if func:
        exceptor = exceptor(func)
    return exceptor


# It exists, so I can import everything at once
# And to add it to other classes for other socials
@attrs
class Browser:
    default_Viewport: dict = attrib(validator=instance_of(dict), default=dict())

    def __attrs_post_init__(self):
        if self.default_Viewport.__len__() == 0:
            self.default_Viewport['isLandscape'] = True

    async def get_browser(
            self,
    ) -> 'BrowserCls':
        return await launch(self.default_Viewport)

    @staticmethod
    async def close_browser(
            browser: BrowserCls,
    ) -> None:
        await browser.close()


class Wait:

    @staticmethod
    @catch_exception
    async def find_xpath(
            page_instance: PageCls,
            xpath: Optional[str] = None,
            options: Optional[dict] = None,
    ) -> 'ElementHandleCls':
        if options:
            el = await page_instance.waitForXPath(xpath, options=options)
        else:
            el = await page_instance.waitForXPath(xpath)
        return el

    @catch_exception
    async def click(
            self,
            page_instance: Optional[PageCls] = None,
            xpath: Optional[str] = None,
            find_options: Optional[dict] = None,
            options: Optional[dict] = None,
            el: Optional[ElementHandleCls] = None,
    ) -> None:
        if not el:
            el = await self.find_xpath(page_instance, xpath, find_options)
        if options:
            await el.click(options)
        else:
            await el.click()

    @catch_exception
    async def screenshot(
            self,
            page_instance: Optional[PageCls] = None,
            xpath: Optional[str] = None,
            options: Optional[dict] = None,
            find_options: Optional[dict] = None,
            el: Optional[ElementHandleCls] = None,
    ) -> None:
        if not el:
            el = await self.find_xpath(page_instance, xpath, find_options)
        if options:
            await el.screenshot(options)
        else:
            await el.screenshot()


@attrs
class RedditScreenshot(Browser, Wait):
    __dark_mode = attrib(validator=instance_of(bool),
                         default=str_to_bool(getenv('DARK_THEME')) if getenv('DARK_THEME') else True)
    __dark_mode_enabled = attrib(default=False)
    __is_nsfw_enabled = attrib(default=False)

    async def dark_theme(
            self,
            page_instance: PageCls,
    ) -> None:
        if self.__dark_mode and not self.__dark_mode_enabled:
            self.__dark_mode_enabled = True

            await self.click(
                page_instance,
                '//*[contains(@class, \'header-user-dropdown\')]',
                {'timeout': 5000},
            )

            # It's normal not to find it, sometimes there is none :shrug:
            await self.click(
                page_instance,
                '//*[contains(text(), \'Settings\')]/ancestor::button[1]',
                {'timeout': 5000},
            )

            await self.click(
                page_instance,
                '//*[contains(text(), \'Dark Mode\')]/ancestor::button[1]',
                {'timeout': 5000},
            )

            # Closes settings
            await self.click(
                page_instance,
                '//*[contains(@class, \'header-user-dropdown\')]',
                {'timeout': 5000},
            )

    async def __call__(
            self,
            browser: 'BrowserCls',
            link: str,
            el_class: str,
            filename: str | int,
            is_nsfw: bool,
    ) -> None:
        reddit_main = await browser.newPage()
        await reddit_main.goto(link)

        await self.dark_theme(reddit_main)

        if is_nsfw and not self.__is_nsfw_enabled:
            self.__is_nsfw_enabled = True
            await self.click(
                reddit_main,
                '//button[contains(text(), \'Yes\')]',
                {'timeout': 5000},
            )

            await self.click(
                reddit_main,
                '//button[contains(text(), \'nsfw\')]',
                {'timeout': 5000},
            )

        await self.screenshot(
            reddit_main,
            f'//*[contains(@id, \'{el_class}\')]',
            {'path': f'assets/img/{filename}.png'},
        )
