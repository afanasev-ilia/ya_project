from django import forms
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import Client, TestCase
from django.urls import reverse
from mixer.backend.django import mixer

from posts.models import Post

User = get_user_model()
INDEX_URL = ('posts:index', 'posts/index.html', None)
POST_CREATE_URL = ('posts:post_create', 'posts/create_post.html', None)


class PostURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.auth = Client()
        cls.author = Client()
        cls.other_auth = Client()
        cls.user = User.objects.create_user(username='user')
        cls.other_user = User.objects.create_user(username='other_user')
        cls.group = mixer.blend('posts.group')
        cls.post = mixer.blend('posts.post', group=cls.group)
        cls.comment = mixer.blend('posts.comment', post=cls.post)
        cls.follow = mixer.blend(
            'posts.follow',
            user=cls.user,
            author=cls.post.author,
        )
        cls.auth.force_login(cls.user)
        cls.author.force_login(cls.post.author)
        cls.other_auth.force_login(cls.other_user)
        cls.group_list_url = (
            'posts:group_list',
            'posts/group_list.html',
            (cls.group.slug,),
        )
        cls.profile_url = (
            'posts:profile',
            'posts/profile.html',
            (cls.post.author,),
        )
        cls.post_url = (
            'posts:post_detail',
            'posts/post_detail.html',
            (cls.post.id,),
        )
        cls.post_edit_url = (
            'posts:post_edit',
            'posts/create_post.html',
            (cls.post.id,),
        )
        cls.follow_index_url = (
            'posts:follow_index',
            'posts/follow.html',
            None,
        )
        cls.paginated = (
            INDEX_URL,
            cls.group_list_url,
            cls.profile_url,
            cls.follow_index_url,
        )
        cls.urls = (
            cls.post_url,
            POST_CREATE_URL,
            cls.post_edit_url,
        ) + cls.paginated

    def setUp(self):
        cache.clear()

    def test_pages_uses_correct_template(self):
        for reverse_name, template, args in self.urls:
            with self.subTest(reverse_name=reverse_name):
                response = self.author.get(
                    reverse(reverse_name, args=args),
                )
                self.assertTemplateUsed(
                    response,
                    template,
                    'URL-адрес не использует соответствующий шаблон',
                )

    def test_pages_index_group_list_profile_show_correct_context(self):
        for reverse_name, _, args in self.paginated:
            with self.subTest(reverse_name=reverse_name):
                response = self.auth.get(
                    reverse(reverse_name, args=args),
                )
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

    def test_post_detail_show_correct_context(self):
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

    def test_create_edit_show_correct_context(self):
        views_names = (
            reverse('posts:post_create'),
            (reverse('posts:post_edit', args=(self.post.id,))),
        )
        for views in views_names:
            response = self.author.get(views)
            form_fields = {
                'text': forms.fields.CharField,
                'group': forms.ModelChoiceField,
                'image': forms.fields.ImageField,
            }
            for value, expected in form_fields.items():
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

    def test_cache_index_ok(self):
        response = self.author.get(reverse('posts:index'))
        before_delete_posts = response.content
        post = Post.objects.get(id=self.post.id)
        post.delete()
        response = self.author.get(reverse('posts:index'))
        after_delete_posts = response.content
        self.assertEqual(before_delete_posts, after_delete_posts)
        cache.clear()
        response = self.author.get(reverse('posts:index'))
        after_cache_clear_posts = response.content
        self.assertNotEqual(before_delete_posts, after_cache_clear_posts)

    def test_author_post_appeared_in_follow_index_follower(self):
        new_post = Post.objects.create(
            author=self.post.author,
            text='Тестовый пост',
            group=self.group,
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

    def test_author_post_not_appeared_in_follow_index_unfollower(self):
        new_post = Post.objects.create(
            author=self.post.author,
            text='Тестовый пост',
            group=self.group,
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
