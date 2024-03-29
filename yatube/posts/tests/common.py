from io import BytesIO
from typing import Tuple

from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

from posts.models import Post


def image(name: str = 'giffy.gif') -> SimpleUploadedFile:
    file = BytesIO()
    Image.new('RGBA', size=(1, 1), color=(155, 0, 0)).save(file, 'gif')
    file.seek(0)
    return SimpleUploadedFile(
        name=name,
        content=file.read(),
        content_type='image/gif',
    )


def postfields_check(
    self,
    got: Post,
    expected: Post,
    fields: Tuple[str, str, str, str] = (
        'text',
        'author',
        'group',
        'image',
    ),
):
    for field in fields:
        with self.subTest(field=field):
            self.assertEqual(
                getattr(got, field),
                getattr(expected, field),
                ('Значения поста в базе не соответсвуют ожидаемым'),
            )
