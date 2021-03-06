from momo import backends
from momo.utils import eval_path, mkdir_p
from momo.core import PLACEHOLDER, Bucket
import os
import yaml


ENV_SETTINGS_DIR = 'MOMO_SETTINGS_DIR'
ENV_SETTINGS_FILE = 'MOMO_SETTINGS_FILE'
ENV_DEFAULT_BUCKET = 'MOMO_DEFAULT_BUCKET'
DEFULT_BUCKET_PATH = eval_path('~/.momo/buckets/default.yml')
DEFAULT_SETTINGS_DIR = eval_path('~/.momo')
DEFAULT_SETTINGS_FILE = os.path.join(DEFAULT_SETTINGS_DIR, 'settings.yml')
BUCKET_FILE_TYPES = {
    'yaml': ('.yaml', '.yml')
}
PROJECT_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), os.pardir))


class SettingsError(Exception):
    pass


class Settings(object):
    """
    The Settings class.

    :param backend: the backend type

    """

    # default settings
    _defaults = {
        'backend': 'yaml',
        'lazy_bucket': True,
        'plugins': {},
        'action': 'default'
    }

    def __init__(self, settings_dir=None, settings_file=None):
        self._backend = self._defaults['backend']
        self._buckets = None
        self._settings = None
        self._cbn = 'default'  # current bucket name
        self.settings_dir = settings_dir or self._get_settings_dir()
        self.settings_file = settings_file or self._get_settings_file()

    def _get_settings_dir(self):
        return os.environ.get(ENV_SETTINGS_DIR) or DEFAULT_SETTINGS_DIR

    def _get_settings_file(self):
        return os.environ.get(ENV_SETTINGS_FILE) or DEFAULT_SETTINGS_FILE

    def load(self):
        if os.path.exists(self.settings_file):
            with open(self.settings_file) as f:
                self._settings = yaml.load(f.read())
            return True
        return False

    def _get_default_bucket_path(self):
        path = os.environ.get(ENV_DEFAULT_BUCKET)
        if path is not None:
            return path
        filetypes = BUCKET_FILE_TYPES[self._backend]
        # for dev
        for ft in filetypes:
            path = os.path.join(PROJECT_PATH, 'momo' + ft)
            if os.path.exists(path):
                return path
        for ft in filetypes:
            path = os.path.join(eval_path('~'), '.momo' + ft)
            if os.path.exists(path):
                return path
        self._create_default_bucket_path()
        return DEFULT_BUCKET_PATH

    def _create_default_bucket_path(self):
        self._create_empty_bucket(DEFULT_BUCKET_PATH)

    def _create_empty_bucket(self, path):
        dirname = os.path.dirname(path)
        mkdir_p(dirname)
        if not os.path.exists(path):
            with open(path, 'w') as f:
                f.write('%s: true' % PLACEHOLDER)

    @property
    def buckets(self):
        """
        Get all buckets as a dictionary of names to paths.

        :return: a dictionary of buckets.

        """
        if self._settings is not None:
            if 'buckets' in self._settings:
                self._buckets = {
                    name: eval_path(path)
                    for name, path in self._settings['buckets'].items()
                }
        if self._buckets is None:
            name = 'default'
            path = self._get_default_bucket_path()
            self._buckets = {
                name: eval_path(path),
            }
        return self._buckets

    def to_bucket(self, name, path):
        BucketDocument = getattr(self.backend, 'BucketDocument')
        document = BucketDocument(name, path)
        return Bucket(document, self)

    @property
    def bucket(self):
        """
        Load the bucket (named self.cbn) from path.
        """
        name = self.cbn
        if name not in self.buckets:
            raise SettingsError('bucket "%s" does not exist' % name)
        path = self.buckets[name]
        if not os.path.exists(path):
            self._create_empty_bucket(path)
        return self.to_bucket(name, path)

    @property
    def backend(self):
        return getattr(backends, self._backend)

    @property
    def cbn(self):
        """
        Get the current bucket name.
        """
        return self._cbn

    @cbn.setter
    def cbn(self, name):
        """Set the current bucket name."""
        self._cbn = name

    def __getattr__(self, name):
        res = None
        if self._settings is not None:
            res = self._settings.get(name)
        if res is None:
            res = self._defaults.get(name)
        if res is None:
            raise SettingsError('"%s" setting is not found' % name)
        return res


settings = Settings()
settings.load()
