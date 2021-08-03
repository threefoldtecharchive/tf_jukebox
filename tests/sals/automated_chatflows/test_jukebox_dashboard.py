import pytest
from jumpscale.loader import j
from solutions_automation import deployer
from .chatflows_base import JukeboxBase
from unittest import TestCase


@pytest.mark.integration
class JukeboxChatflows(JukeboxBase):

    def tearDown(self):
        self.info("Delete a solution")
        if self.solution_name:
            j.sals.jukebox.delete(self.solution_name)

        j.sals.process.execute(f"sudo wg-quick down {self.wg_path}")
        j.sals.fs.rmtree(path=self.wg_path)

        super().tearDown()

    def test_01_deploy_dash(self):
        """Test case for deploying a dash.

        **Test Scenario**

        - Deploy a dash.
        - Get and up wireguard.
        - Check that dash has been reachable.
        """

        self.info("Deploy a dash")
        self.solution_name = self.random_name().lower()
        expiration = j.data.time.utcnow().timestamp + 60 * 60 * 24 # expiraion after one day
        self.dash = deployer.deploy_dash(self.solution_name, expiration_time=expiration,)

        self.info("Get and up wireguard")
        self.wg_path = f"/tmp/{self.random_name()}.conf"
        j.sals.fs.write_file(self.wg_path, self.dash.wg_quick )
        rc, out, err = j.sals.process.execute(f"sudo wg-quick up {self.wg_path}")
        TestCase().assertFalse(rc, f"out: {out} err: {err}")

        self.info("Check that dash has been reachable")
        self.solution_name = f"dash_jukebox_{self.tname.replace('.3bot', '')}_{self.solution_name}"
        dash = j.sals.jukebox.get(self.solution_name)

        request = j.tools.http.get(f"http://{dash.nodes[0].ipv4_address}", timeout=60)
        self.assertEqual(request.status_code, 200)

    def test_02_deploy_digibyte(self):
        """Test case for deploying a digibyte.

        **Test Scenario**

        - Deploy a digibyte.
        - Get and up wireguard.
        - Check that digibyte has been reachable.
        """

        self.info("Deploy a digibyte")
        self.solution_name = self.random_name().lower()
        expiration = j.data.time.utcnow().timestamp + 60 * 60 * 24 # expiraion after one day
        self.digibyte = deployer.deploy_digibyte(self.solution_name, expiration_time=expiration,)

        self.info("Get and up wireguard")
        self.wg_path = f"/tmp/{self.random_name()}.conf"
        j.sals.fs.write_file(self.wg_path, self.digibyte.wg_quick)
        rc, out, err = j.sals.process.execute(f"sudo wg-quick up {self.wg_path}")
        TestCase().assertFalse(rc, f"out: {out} err: {err}")

        self.info("Check that digibyte has been reachable")
        self.solution_name = f"digibyte_jukebox_{self.tname.replace('.3bot', '')}_{self.solution_name}"
        digibyte = j.sals.jukebox.get(self.solution_name)

        request = j.tools.http.get(f"http://{digibyte.nodes[0].ipv4_address}", timeout=60)
        self.assertEqual(request.status_code, 200)

    def test_03_deploy_presearch(self):
        """Test case for deploying a presearch.

        **Test Scenario**

        - Deploy a presearch.
        - Get and up wireguard.
        - Check that presearch has been reachable.
        """

        self.info("Deploy a presearch")
        self.solution_name = self.random_name().lower()
        register_code = self.random_name()
        expiration = j.data.time.utcnow().timestamp + 60 * 60 * 24 # expiraion after one day
        self.presearch = deployer.deploy_presearch(self.solution_name, expiration_time=expiration, register_code=register_code)

        self.info("Get and up wireguard")
        self.wg_path = f"/tmp/{self.random_name()}.conf"
        j.sals.fs.write_file(self.wg_path, self.presearch.wg_quick)
        rc, out, err = j.sals.process.execute(f"sudo wg-quick up {self.wg_path}")
        TestCase().assertFalse(rc, f"out: {out} err: {err}")

        self.info("Check that presearch has been reachable")
        self.solution_name = f"presearch_jukebox_{self.tname.replace('.3bot', '')}_{self.solution_name}"
        presearch = j.sals.jukebox.get(self.solution_name)

        request = j.tools.http.get(f"http://{presearch.nodes[0].ipv4_address}", timeout=60)
        self.assertEqual(request.status_code, 200)
