from django import forms
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import Client, TestCase
from django.urls import reverse
from mixer.backend.django import mixer

from posts.models import Post

User = get_user_model()


class PostURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.auth = Client()
        cls.author = Client()
        cls.other_auth = Client()

        cls.user, cls.author_user, cls.other_user = mixer.cycle(3).blend(User)

        cls.auth.force_login(cls.user)
        cls.author.force_login(cls.author_user)
        cls.other_auth.force_login(cls.other_user)

        cls.group = mixer.blend('posts.group')
        cls.post = mixer.blend(
            'posts.post',
            author=cls.author_user,
            group=cls.group,
        )
        cls.comment = mixer.blend('posts.comment', post=cls.post)
        cls.follow = mixer.blend(
            'posts.follow',
            user=cls.user,
            author=cls.post.author,
        )
        cls.urls = {
            'index': reverse('posts:index'),
            'post_create': reverse('posts:post_create'),
            'group_list': reverse('posts:group_list', args=(cls.group.slug,)),
            'profile': reverse(
                'posts:profile',
                args=(cls.author_user.username,),
            ),
            'post_detail': reverse('posts:post_detail', args=(cls.post.id,)),
            'post_edit': reverse('posts:post_edit', args=(cls.post.id,)),
            'follow_index': reverse('posts:follow_index'),
        }

    def setUp(self):
        cache.clear()

    def test_pages_index_group_list_profile_show_correct_context(self) -> None:
        paginated = (
            self.urls.get('index'),
            self.urls.get('group_list'),
            self.urls.get('profile'),
            self.urls.get('follow_index'),
        )
        for address in paginated:
            with self.subTest(address=address):
                response = self.auth.get(address)
                post = response.context['page_obj'][0]
                contexts = (
                    ('text', self.post.text),
                    ('author', self.post.author),
                    ('group', self.post.group),
                    ('image', self.post.image),
                )
                for field, cont in contexts:
                    with self.subTest(field=field):
                        self.assertEqual(
                            getattr(post, field),
                            cont,
                            (
                                'Шаблоны index, group_list, profile '
                                'сформированы с некорректным контекстом'
                            ),
                        )

    def test_post_detail_show_correct_context(self) -> None:
        response = self.author.get(
            reverse(
                'posts:post_detail',
                args=(self.post.id,),
            ),
        )
        post = response.context['post']
        comment = response.context['comments'][0]
        self.assertEqual(
            post,
            self.post,
            'Шаблон post_detail сформирован с некорректным контекстом',
        )
        self.assertEqual(
            post.text,
            self.post.text,
            'Шаблон post_detail сформирован с некорректным контекстом',
        )
        self.assertEqual(
            post.author,
            self.post.author,
            'Шаблон post_detail сформирован с некорректным контекстом',
        )
        self.assertEqual(
            post.group,
            self.post.group,
            'Шаблон post_detail сформирован с некорректным контекстом',
        )
        self.assertEqual(
            comment.author,
            self.comment.author,
            'Шаблон post_detail сформирован с некорректным контекстом',
        )
        self.assertEqual(
            comment.text,
            self.comment.text,
            'Шаблон post_detail сформирован с некорректным контекстом',
        )

    def test_create_edit_show_correct_context(self) -> None:
        views_names = (
            reverse('posts:post_create'),
            (reverse('posts:post_edit', args=(self.post.id,))),
        )
        for views in views_names:
            response = self.author.get(views)
            form_fields = (
                ('text', forms.fields.CharField),
                ('group', forms.ModelChoiceField),
                ('image', forms.fields.ImageField),
            )
            for value, expected in form_fields:
                with self.subTest(value=value):
                    form_field = response.context.get('form').fields.get(value)
                    self.assertIsInstance(
                        form_field,
                        expected,
                        (
                            'Шаблоны post_create, post_edit'
                            'сформированы с некорректным контекстом.'
                        ),
                    )

    def test_cache_index_ok(self) -> None:
        before_delete_posts = self.author.get(reverse('posts:index')).content
        post = Post.objects.get(id=self.post.id)

        post.delete()
        after_delete_posts = self.author.get(reverse('posts:index')).content
        self.assertEqual(before_delete_posts, after_delete_posts)

        cache.clear()
        after_cache_clear_posts = self.author.get(
            reverse('posts:index'),
        ).content
        self.assertNotEqual(before_delete_posts, after_cache_clear_posts)

    def test_author_post_appeared_in_follow_index_follower(self) -> None:
        new_post = mixer.blend(
            'posts.post',
            author=self.post.author,
        )
        response = self.auth.get(reverse('posts:follow_index'))
        post = response.context['page_obj'][0]
        contexts = (
            ('text', new_post.text),
            ('author', new_post.author),
            ('group', new_post.group),
        )
        for field, cont in contexts:
            with self.subTest(field=field):
                self.assertEqual(
                    getattr(post, field),
                    cont,
                    (
                        'Пост автора не повяляется в follow_index '
                        'подписанного пользователя'
                    ),
                )

    def test_author_post_not_appeared_in_follow_index_unfollower(self) -> None:
        new_post = mixer.blend(
            'posts.post',
            author=self.post.author,
        )
        response = self.other_auth.get(reverse('posts:follow_index'))
        self.assertNotIn(
            new_post,
            response.context['page_obj'].object_list,
            (
                'Пост автора не повяляется в follow_index '
                'подписанного пользователя'
            ),
        )
