import subprocess

def define_env(env):
    @env.macro
    def get_git_tags():
        try:
            output = subprocess.check_output(['git', 'tag', '--sort=-creatordate'], text=True)
            tags = [t.strip() for t in output.split('
') if t.strip()]
            return tags
        except Exception:
            return []
